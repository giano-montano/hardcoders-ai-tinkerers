"""Bot de Telegram: pide distrito de Lima y una foto de receta médica.

Flujo:
    1. Primer mensaje / /start -> pregunta el distrito de Lima
    2. Distrito válido         -> pide la foto de la receta
    3. Llega la foto           -> la descarga y llama a receta.analizar_receta()

Long polling con stdlib (sin dependencias). Ejecutar:
    python bot.py
Requiere TELEGRAM_BOT_TOKEN en .env
"""

import json
import os
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

from receta import analizar_receta

API = "https://api.telegram.org/bot{token}/{method}"
ARCHIVOS = "https://api.telegram.org/file/bot{token}/{ruta}"
DIR_RECETAS = os.path.join("data", "recetas")

# --- Pasos del flujo ----------------------------------------------------------
PEDIR_DISTRITO = "pedir_distrito"
PEDIR_FOTO = "pedir_foto"

# Estado en memoria: {chat_id: {"paso": str, "distrito": str, "recetas": [str]}}
ESTADO: dict[int, dict] = {}

DISTRITOS = [
    "Ancón", "Ate", "Barranco", "Breña", "Carabayllo", "Cercado de Lima",
    "Chaclacayo", "Chorrillos", "Cieneguilla", "Comas", "El Agustino",
    "Independencia", "Jesús María", "La Molina", "La Victoria", "Lince",
    "Los Olivos", "Lurigancho", "Lurín", "Magdalena del Mar", "Miraflores",
    "Pachacámac", "Pucusana", "Pueblo Libre", "Puente Piedra", "Punta Hermosa",
    "Punta Negra", "Rímac", "San Bartolo", "San Borja", "San Isidro",
    "San Juan de Lurigancho", "San Juan de Miraflores", "San Luis",
    "San Martín de Porres", "San Miguel", "Santa Anita", "Santa María del Mar",
    "Santa Rosa", "Santiago de Surco", "Surquillo", "Villa El Salvador",
    "Villa María del Triunfo",
]

ALIAS = {
    "lima": "Cercado de Lima",
    "lima cercado": "Cercado de Lima",
    "centro de lima": "Cercado de Lima",
    "sjl": "San Juan de Lurigancho",
    "san juan lurigancho": "San Juan de Lurigancho",
    "sjm": "San Juan de Miraflores",
    "smp": "San Martín de Porres",
    "vmt": "Villa María del Triunfo",
    "ves": "Villa El Salvador",
    "surco": "Santiago de Surco",
}

# Todo texto que ve el usuario va en inglés (es lo que se proyecta en la demo).
# Ver AGENTS.md.
MSG_DISTRITO = (
    "Hi 👋 I'm your prescription assistant.\n\n"
    "Which *district of Lima* are you in? (type it, e.g. Miraflores)"
)
MSG_DISTRITO_INVALIDO = (
    "I don't recognize that district 🤔 Try typing it in full, for example: "
    "San Isidro, Comas, Villa El Salvador…"
)
MSG_PEDIR_FOTO = (
    "Great, {distrito} ✅\n\n"
    "Now send me a *photo of your medical prescription* 📄📷\n"
    "Make sure the medicine names are readable."
)
MSG_FALTA_FOTO = "I need a photo 📷 of the prescription to read it."
MSG_PROCESANDO = "Got your prescription, analyzing it… ⏳"
MSG_SOLO_FOTO = "Please send it as a *photo*, not as a file attachment 📷"
MSG_ERROR_ANALISIS = "Oops, the prescription analysis failed 😵 Please try again."


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower().strip())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


DISTRITOS_NORM = {normalizar(d): d for d in DISTRITOS}


def buscar_distrito(texto: str) -> str | None:
    """Devuelve el nombre canónico del distrito, o None si no coincide."""
    clave = normalizar(texto)
    if not clave:
        return None
    if clave in DISTRITOS_NORM:
        return DISTRITOS_NORM[clave]
    if clave in ALIAS:
        return ALIAS[clave]
    candidatos = {orig for norm, orig in DISTRITOS_NORM.items() if clave in norm}
    return candidatos.pop() if len(candidatos) == 1 else None


def cargar_env(ruta=".env"):
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def api(token, metodo, **params):
    url = API.format(token=token, method=metodo)
    datos = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=datos)
    with urllib.request.urlopen(req, timeout=65) as r:
        return json.load(r)


def enviar(token, chat_id, texto):
    api(token, "sendMessage", chat_id=chat_id, text=texto, parse_mode="Markdown")


def descargar_foto(token, mensaje, chat_id) -> str:
    """Descarga la foto de mayor resolución del mensaje y devuelve la ruta local."""
    file_id = mensaje["photo"][-1]["file_id"]  # la última es la más grande
    info = api(token, "getFile", file_id=file_id)["result"]
    url = ARCHIVOS.format(token=token, ruta=info["file_path"])
    os.makedirs(DIR_RECETAS, exist_ok=True)
    ext = os.path.splitext(info["file_path"])[1] or ".jpg"
    destino = os.path.join(DIR_RECETAS, f"{chat_id}_{mensaje['message_id']}{ext}")
    with urllib.request.urlopen(url, timeout=60) as r, open(destino, "wb") as f:
        f.write(r.read())
    return destino


def manejar(token, mensaje):
    chat_id = mensaje["chat"]["id"]
    texto = (mensaje.get("text") or "").strip()
    estado = ESTADO.setdefault(
        chat_id, {"paso": PEDIR_DISTRITO, "distrito": "", "recetas": []}
    )

    # /start reinicia siempre el flujo
    if texto == "/start":
        ESTADO[chat_id] = {"paso": PEDIR_DISTRITO, "distrito": "", "recetas": []}
        enviar(token, chat_id, MSG_DISTRITO)
        return

    # --- Paso 1: distrito -----------------------------------------------------
    if estado["paso"] == PEDIR_DISTRITO:
        if not texto:
            enviar(token, chat_id, MSG_DISTRITO)
            return
        distrito = buscar_distrito(texto)
        if not distrito:
            enviar(token, chat_id, MSG_DISTRITO_INVALIDO)
            return
        estado["distrito"] = distrito
        estado["paso"] = PEDIR_FOTO
        enviar(token, chat_id, MSG_PEDIR_FOTO.format(distrito=distrito))
        return

    # --- Paso 2: foto de la receta -------------------------------------------
    if not mensaje.get("photo"):
        if mensaje.get("document"):
            enviar(token, chat_id, MSG_SOLO_FOTO)
        else:
            enviar(token, chat_id, MSG_FALTA_FOTO)
        return

    enviar(token, chat_id, MSG_PROCESANDO)
    ruta = descargar_foto(token, mensaje, chat_id)
    estado["recetas"].append(ruta)

    # --- Paso 3: handoff al analizador (lo implementa otra persona) -----------
    try:
        resultado = analizar_receta(ruta, estado["distrito"], chat_id)
    except Exception as e:
        print("error en analizar_receta:", e)
        enviar(token, chat_id, MSG_ERROR_ANALISIS)
        return

    enviar(token, chat_id, resultado.get("mensaje") or "Done.")
    # Se queda en PEDIR_FOTO: puede mandar otra receta sin repetir el distrito.


def main():
    cargar_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        sys.exit("Falta TELEGRAM_BOT_TOKEN en .env")

    yo = api(token, "getMe")
    print(f"Bot activo: @{yo['result']['username']}  (Ctrl+C para parar)")

    offset = 0
    while True:
        try:
            res = api(token, "getUpdates", offset=offset, timeout=50)
        except Exception as e:  # red caída, timeout, etc.
            print("error de red:", e)
            time.sleep(3)
            continue

        for upd in res.get("result", []):
            offset = upd["update_id"] + 1
            mensaje = upd.get("message") or upd.get("edited_message")
            if not mensaje:
                continue
            try:
                manejar(token, mensaje)
            except Exception as e:
                print("error manejando mensaje:", e)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAdiós.")
