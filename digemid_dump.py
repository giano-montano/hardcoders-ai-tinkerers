"""Descarga la base de precios de DIGEMID (OPM) a CSV y XLSX.

Stdlib pura, sin `pip install` (ver AGENTS.md).

Uso típico (lo que sirve para la hackathon):

    python digemid_dump.py grupos                      # 1) catálogo de productos (~26 llamadas)
    python digemid_dump.py precios --departamento 15   # 2) precios de todo Lima -> CSV
    python digemid_dump.py xlsx                        # 3) CSV -> XLSX (parte si excede el límite)

Otros:

    python digemid_dump.py catalogo                    # XLSX oficial de productos (1 llamada)
    python digemid_dump.py precios --ubigeo 150116     # solo Lince (rápido, para probar)
    python digemid_dump.py precios                     # TODO el Perú (~31M filas, ~1.5 h, varios GB)

El dump de precios es **reanudable**: si lo cortas, vuelve a correrlo y sigue
donde quedó (se apoya en `data/digemid/_hechos.txt`).
"""

import argparse
import csv
import json
import os
import string
import sys
import time
import urllib.error
import urllib.request
import zipfile
from xml.sax.saxutils import escape

BASE = "https://ms-opm.minsa.gob.pe/msopmcovid"

# El WAF de MINSA responde 403 sin User-Agent de navegador. Origin/Referer también
# hacen falta. `tokenGoogle` es reCAPTCHA v3 pero el backend NO lo valida: va vacío.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://opm-digemid.minsa.gob.pe",
    "Referer": "https://opm-digemid.minsa.gob.pe/",
}

DIR = os.path.join("data", "digemid")
GRUPOS_JSON = os.path.join(DIR, "grupos.json")
PRECIOS_CSV = os.path.join(DIR, "precios.csv")
HECHOS_TXT = os.path.join(DIR, "_hechos.txt")
CATALOGO_XLSX = os.path.join(DIR, "catalogo_productos.xlsx")

# Columnas del CSV, en el orden en que se escriben.
COLUMNAS = [
    "nombreProducto", "concent", "nombreFormaFarmaceutica", "nombreComercial",
    "precio2", "precio1", "fracciones", "departamento", "provincia", "distrito",
    "direccion", "telefono", "setcodigo", "fecha", "nombreLaboratorio",
    "nombreTitular", "codEstab", "codProdE", "ubicodigo", "catCodigo",
]

PAUSA = 0.4  # segundos entre llamadas: es un servidor del Estado, no lo martillemos.
MAX_FILAS_HOJA = 1_048_575  # límite de Excel (1_048_576 menos la fila de cabecera)


# --- HTTP ---------------------------------------------------------------------

def post(ruta, filtro, timeout=120, reintentos=3):
    """POST {"filtro": ...} al backend. Reintenta con backoff ante fallos de red."""
    cuerpo = json.dumps({"filtro": filtro}).encode()
    for intento in range(reintentos):
        try:
            req = urllib.request.Request(f"{BASE}/{ruta}", data=cuerpo, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if intento == reintentos - 1:
                raise
            espera = 2 ** intento
            print(f"    reintento {intento + 1}/{reintentos} en {espera}s ({e})")
            time.sleep(espera)


def descargar(ruta, filtro, destino, timeout=300):
    """POST que devuelve un binario (XLSX) y lo guarda en disco."""
    cuerpo = json.dumps({"filtro": filtro}).encode()
    req = urllib.request.Request(f"{BASE}/{ruta}", data=cuerpo, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r, open(destino, "wb") as f:
        f.write(r.read())
    return os.path.getsize(destino)


# --- Comandos -----------------------------------------------------------------

def cmd_catalogo(args):
    """Baja el XLSX oficial del catálogo de productos (lo genera el propio DIGEMID)."""
    os.makedirs(DIR, exist_ok=True)
    n = descargar("producto/catalogoproductos",
                  {"situacion": "ACT", "tokenGoogle": ""}, CATALOGO_XLSX)
    print(f"✓ {CATALOGO_XLSX} ({n:,} bytes)")


def cmd_grupos(args):
    """Enumera los productos barriendo el autocomplete con cada letra A-Z.

    El endpoint ignora `tamanio` y devuelve todo lo que matchea por substring,
    así que 26 llamadas cubren el catálogo completo. La identidad de un producto
    es la terna (grupo, codGrupoFF, concent).
    """
    os.makedirs(DIR, exist_ok=True)
    grupos = {}
    for ch in string.ascii_uppercase:
        d = post("producto/autocompleteciudadano",
                 {"nombreProducto": ch, "pagina": 1, "tamanio": 5000, "tokenGoogle": ""})
        for p in d.get("data") or []:
            grupos[(p["grupo"], p["codGrupoFF"], p["concent"])] = p["nombreProducto"]
        print(f"  {ch}: {len(d.get('data') or []):>5} filas | únicos: {len(grupos)}")
        time.sleep(PAUSA)

    salida = [{"grupo": g, "codGrupoFF": ff, "concent": c, "nombreProducto": n}
              for (g, ff, c), n in grupos.items()]
    with open(GRUPOS_JSON, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    print(f"✓ {len(salida):,} grupos -> {GRUPOS_JSON}")


def cmd_precios(args):
    """Recorre los grupos y vuelca todos los precios a CSV. Reanudable."""
    if not os.path.exists(GRUPOS_JSON):
        sys.exit(f"Falta {GRUPOS_JSON}. Corre primero: python digemid_dump.py grupos")

    with open(GRUPOS_JSON, encoding="utf-8") as f:
        grupos = json.load(f)

    # Reanudación: saltamos los grupos ya volcados en una corrida anterior.
    hechos = set()
    if os.path.exists(HECHOS_TXT):
        with open(HECHOS_TXT, encoding="utf-8") as f:
            hechos = {l.strip() for l in f if l.strip()}
        print(f"reanudando: {len(hechos):,} grupos ya hechos")

    nuevo = not os.path.exists(PRECIOS_CSV) or not hechos
    modo = "w" if nuevo else "a"
    filas_tot = 0
    t0 = time.time()

    with open(PRECIOS_CSV, modo, encoding="utf-8-sig", newline="") as fcsv, \
         open(HECHOS_TXT, "a", encoding="utf-8") as fh:
        w = csv.DictWriter(fcsv, fieldnames=COLUMNAS, extrasaction="ignore")
        if nuevo:
            w.writeheader()

        for i, g in enumerate(grupos, 1):
            clave = f"{g['grupo']}|{g['codGrupoFF']}|{g['concent']}"
            if clave in hechos:
                continue
            try:
                d = post("preciovista/ciudadano", {
                    "codigoProducto": g["grupo"],
                    "codGrupoFF": g["codGrupoFF"],
                    "concent": g["concent"],
                    "codigoDepartamento": args.departamento,
                    "codigoProvincia": args.provincia,
                    "codigoUbigeo": args.ubigeo,
                    "codTipoEstablecimiento": None, "catEstablecimiento": None,
                    "nombreEstablecimiento": None, "nombreLaboratorio": None,
                    "nombreProducto": None,
                    "tamanio": 100000, "pagina": 1, "tokenGoogle": "",
                })
            except Exception as e:
                print(f"  [{i}/{len(grupos)}] ERROR {g['nombreProducto'][:30]}: {e}")
                continue

            filas = d.get("data") or []
            for row in filas:
                w.writerow(row)
            filas_tot += len(filas)
            fh.write(clave + "\n")
            fh.flush()
            fcsv.flush()

            if i % 25 == 0 or filas:
                tr = time.time() - t0
                print(f"  [{i}/{len(grupos)}] {g['nombreProducto'][:28]:<28} "
                      f"+{len(filas):>6} | total {filas_tot:>9,} | {tr/60:.1f} min")
            time.sleep(PAUSA)

    print(f"✓ {filas_tot:,} filas nuevas -> {PRECIOS_CSV}")


# --- Escritura de XLSX con stdlib (zipfile + XML) ------------------------------

def _hoja_xml(filas, columnas):
    """Genera el XML de una hoja usando inlineStr (evita sharedStrings)."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
           "<sheetData>"]
    for n, fila in enumerate([columnas] + filas, 1):
        out.append(f'<row r="{n}">')
        for j, val in enumerate(fila):
            ref = ""
            col = j
            while True:
                ref = chr(ord("A") + col % 26) + ref
                col = col // 26 - 1
                if col < 0:
                    break
            val = "" if val is None else str(val)
            # Los números se escriben como número; el resto como texto inline.
            try:
                if val.strip() == "":
                    raise ValueError
                float(val)
                out.append(f'<c r="{ref}{n}"><v>{escape(val)}</v></c>')
            except ValueError:
                out.append(f'<c r="{ref}{n}" t="inlineStr">'
                           f"<is><t>{escape(val)}</t></is></c>")
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def escribir_xlsx(destino, columnas, filas):
    """Escribe un XLSX mínimo pero válido (una hoja)."""
    ct = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>")
    wb = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="precios" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wbrels = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
              "</Relationships>")

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbrels)
        z.writestr("xl/worksheets/sheet1.xml", _hoja_xml(filas, columnas))


def cmd_xlsx(args):
    """Convierte el CSV a XLSX, partiéndolo si excede el límite de filas de Excel."""
    origen = args.csv or PRECIOS_CSV
    if not os.path.exists(origen):
        sys.exit(f"No existe {origen}. Corre primero: python digemid_dump.py precios")

    with open(origen, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        columnas = next(r)
        parte, filas, hechos = 1, [], 0
        for fila in r:
            filas.append(fila)
            if len(filas) >= MAX_FILAS_HOJA:
                destino = origen.replace(".csv", f"_parte{parte}.xlsx")
                escribir_xlsx(destino, columnas, filas)
                print(f"✓ {destino} ({len(filas):,} filas)")
                hechos += len(filas)
                filas, parte = [], parte + 1
        if filas or parte == 1:
            destino = (origen.replace(".csv", ".xlsx") if parte == 1
                       else origen.replace(".csv", f"_parte{parte}.xlsx"))
            escribir_xlsx(destino, columnas, filas)
            print(f"✓ {destino} ({len(filas):,} filas)")
            hechos += len(filas)
    print(f"total: {hechos:,} filas")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalogo", help="XLSX oficial del catálogo de productos")
    sub.add_parser("grupos", help="enumera productos (A-Z) -> grupos.json")

    pp = sub.add_parser("precios", help="vuelca precios a CSV (reanudable)")
    pp.add_argument("--departamento", default=None, help='ej. "15" (Lima)')
    pp.add_argument("--provincia", default=None, help='ej. "01" (Lima)')
    pp.add_argument("--ubigeo", default=None, help='distrito, ej. "150116" (Lince)')

    px = sub.add_parser("xlsx", help="CSV -> XLSX (parte a 1,048,575 filas)")
    px.add_argument("--csv", default=None, help="CSV de entrada")

    args = p.parse_args()
    {"catalogo": cmd_catalogo, "grupos": cmd_grupos,
     "precios": cmd_precios, "xlsx": cmd_xlsx}[args.cmd](args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCortado. Volvé a correr el mismo comando para reanudar.")
