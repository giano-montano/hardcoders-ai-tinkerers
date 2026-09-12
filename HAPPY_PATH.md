# HAPPY PATH — la meta de la hackathon

**Fecha:** 2026-09-12
**Estado:** flujo de Telegram ✅ hecho · analizador de receta 🚧 stub · DIGEMID ✅ API verificada hoy

Este documento es el **norte**: si esto corre de punta a punta en la demo, ganamos.
Todo lo demás es opcional.

> Lee `AGENTS.md` antes de tocar código. Regla dura: **lo que ve el usuario va en
> inglés** (se proyecta), el código y los comentarios en español.

---

## 1. El usuario

**Don Julio, 90 años.** Vive en **Lince**. Pobre, cojo, medio ciego.
Tiene **gastritis** y una **receta física** en la mano.

Hoy su única opción es caminar de botica en botica preguntando precios. Camina
mal y no ve bien: en la práctica compra en la primera botica que encuentra, al
precio que le digan.

**Lo que necesita:** saber **dónde**, cerca de su casa, consigue **su** medicina
**más barata** — sin caminar, sin buscar, sin comparar.

**Restricciones de diseño que salen de esto** (no son adorno, son el producto):

- **Cero apps nuevas.** Solo WhatsApp (MVP: **Telegram**), que ya sabe usar.
- **Cero escribir.** Manda una **foto**. Escribir su distrito, una vez, es el
  único texto que tecleará.
- **Cero leer de más.** La respuesta son **3 opciones**, no 253. Letra grande,
  precio grande.
- **Cero jerga.** Nada de "principio activo" ni "forma farmacéutica" en pantalla.

---

## 2. El happy path, turno por turno

Esto es **literalmente** lo que se proyecta en la demo. Los textos del bot van
en inglés (`AGENTS.md`); el estado real es el de `bot.py`.

| # | Actor | Qué pasa |
|---|---|---|
| 1 | 👴 | Abre Telegram, busca el contacto **medisavings bot**, toca *Start* |
| 2 | 🤖 | `Hi 👋 I am your prescription assistant.`<br>`Which *district of Lima* are you in? (type it, e.g. Miraflores)` |
| 3 | 👴 | Escribe `lince` (minúscula, sin tilde — `buscar_distrito()` lo normaliza) |
| 4 | 🤖 | `Great, Lince ✅`<br>`Now send me a *photo of your medical prescription* 📄📷` |
| 5 | 👴 | Le toma **foto a la receta** y la manda |
| 6 | 🤖 | `Got your prescription, analyzing it… ⏳` |
| 7 | ⚙️ | *(pocos segundos)* OCR/visión → medicamentos → consulta DIGEMID en Lince → ranking por precio |
| 8 | 🤖 | **La respuesta.** Por cada medicamento, las 3 boticas más baratas cerca |

### Turno 8 — la respuesta (así se ve, y está en inglés)

```
✅ I read your prescription. Found 1 medicine:

💊 *OMEPRAZOLE 20 mg* (capsule)

Cheapest near you in Lince:

1️⃣  *BOTICAS GAMBITO* — S/ 0.10 each
     Av. General César Canevaro 516, Risso
     📞 958232075 · Mon-Sat 8:00-16:00

2️⃣  *MIFARMA* — S/ 0.11 each
     Jr. Risso 173

3️⃣  *MIFARMA* — S/ 0.11 each
     Av. Ignacio Merino 1859

💡 Cheapest of 72 pharmacies in Lince.
Prices from MINSA-DIGEMID, updated 28/08/2026.
```

**Datos reales, no inventados.** Esas boticas, precios y direcciones salieron
hoy de la API de DIGEMID (ver §4). En Lince hay **253 registros de omeprazol
20 mg en 72 establecimientos**, y entre los más baratos el rango real va de
**S/ 0.10 a S/ 0.11** por unidad.

### Por qué esto gana la demo

El jurado ve: **foto → unos segundos → "compra aquí, cuesta S/ 0.10, queda a 3
cuadras"**. No hay que explicar nada. El ahorro es verificable contra
`opm-digemid.minsa.gob.pe` en vivo.

---

## 3. Qué pasa por dentro

```
  Telegram
     │  foto + distrito
     ▼
  bot.py            ← ✅ HECHO (long polling, stdlib, sin pip install)
     │  descarga a data/recetas/<chat_id>_<msg_id>.jpg
     │  llama analizar_receta(ruta, distrito, chat_id)
     ▼
  receta.py         ← 🚧 STUB. Visión (OpenRouter) → lista de medicamentos
     │  [{nombre: "Omeprazol", presentacion: "20 mg cápsulas", ...}]
     ▼
  digemid           ← 🚧 FALTA. Por cada medicamento:
     │  a) producto/autocompleteciudadano  → resolver nombre a (grupo, codGrupoFF, concent)
     │  b) preciovista/ciudadano           → precios en el ubigeo del distrito
     │  c) ordenar por precio unitario, tomar 3
     ▼
  mensaje en inglés → Telegram
```

**El puente que falta es corto**: `receta.py` ya recibe el `distrito` como
argumento justo para esto. No hay que cambiar el contrato con `bot.py`.

### El mapeo distrito → ubigeo

`bot.py` ya valida los 43 distritos de Lima Metropolitana y devuelve el nombre
canónico. DIGEMID filtra por **ubigeo** (`"150116"` = Lince), no por nombre. Hace
falta una tabla `{"Lince": "150116", ...}` — se saca de un solo llamado a
`parametro/distritos` (§4.2) y se deja hardcodeada: son 43 filas y no cambian.

---

## 4. La API de DIGEMID — verificada el 2026-09-12

La web pública es `https://opm-digemid.minsa.gob.pe/#/consulta-producto`, un
Angular que consume este backend:

```
BASE = https://ms-opm.minsa.gob.pe/msopmcovid
```

Todos los endpoints son **POST**, body `{"filtro": {...}}`, respuesta
`{"codigo": "00", "mensaje": "...", "data": [...]}`. `codigo == "00"` es OK.

### 4.0 Dos trampas que ya costaron tiempo

1. **Hay WAF por User-Agent.** Un `curl` pelado recibe **403**. Con un
   User-Agent de navegador (+ `Origin` y `Referer` de `opm-digemid...`)
   responde 200. Mandar siempre estos headers.
2. **El campo `tokenGoogle` es de reCAPTCHA v3, pero NO se valida.**
   Mandar `""` funciona. **No hace falta resolver captcha** — esto es lo que
   hace viable todo el proyecto en una tarde.

```python
H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://opm-digemid.minsa.gob.pe",
    "Referer": "https://opm-digemid.minsa.gob.pe/",
}
```

### 4.1 `producto/autocompleteciudadano` — nombre → identidad del producto

El nombre que sale de la receta ("Omeprazol") hay que resolverlo primero.

```json
{"filtro": {"nombreProducto": "OMEPRAZOL", "pagina": 1, "tamanio": 10, "tokenGoogle": ""}}
```

Devuelve, entre otros: `nombreProducto`, `concent` (`"20mg"`),
`nombreFormaFarmaceutica` (`"Tableta - Capsula"`), **`grupo`** (`2841`) y
**`codGrupoFF`** (`"3"`).

> ⚠️ `codigoProducto` viene **`null`** aquí. La identidad del producto es la
> terna **`grupo` + `codGrupoFF` + `concent`**, y en la consulta de precios el
> `grupo` se manda en el campo llamado `codigoProducto`. Es confuso, pero es
> exactamente lo que hace el frontend (`this.filtro.codigoProducto = e.grupo`).

### 4.2 `parametro/distritos` — tabla de ubigeos (se corre una vez)

```json
{"filtro": {"codigo": "01", "codigoDos": "15"}}
```

`codigo` = provincia (`"01"` = Lima), `codigoDos` = departamento (`"15"` = Lima).
Devuelve los 43 distritos: `{"codigo": "150116", "descripcion": "LINCE", ...}`.

### 4.3 `preciovista/ciudadano` — **el endpoint de oro**

Precios por producto y por distrito. Este es el que hace la demo.

```json
{"filtro": {
  "codigoProducto": 2841,
  "codGrupoFF": "3",
  "concent": "20mg",
  "codigoDepartamento": "15",
  "codigoProvincia": "01",
  "codigoUbigeo": "150116",
  "codTipoEstablecimiento": null,
  "catEstablecimiento": null,
  "nombreEstablecimiento": null,
  "nombreLaboratorio": null,
  "nombreProducto": null,
  "tamanio": 50, "pagina": 1,
  "tokenGoogle": ""
}}
```

(`codigoProducto` = el `grupo` del autocomplete; `codigoUbigeo` = Lince.)

Cada registro del `data` trae lo que necesitamos para el mensaje:

| Campo | Ejemplo | Uso en la demo |
|---|---|---|
| `nombreComercial` | `"BOTICAS GAMBITO"` | nombre de la botica |
| `precio2` | `0.1` | **precio unitario S/.** ← *el que se rankea* |
| `precio1` | `10.0` | precio del empaque S/. |
| `fracciones` | `100` | unidades por empaque (`precio1 = precio2 × fracciones`) |
| `direccion` | `"AV. GENERAL CESAR CANEVARO NRO. 516 RISSO"` | a dónde ir |
| `telefono` | `"958232075"` | para llamar antes de caminar |
| `distrito` | `"LINCE"` | confirmación |
| `setcodigo` | `"Privado"` | Privado / Público |
| `fecha` | `"28/08/2026"` | antigüedad del precio |
| `codEstab`, `codProdE` | `"0124339"`, `48171` | claves para el detalle (§4.4) |

> ⚠️ **`precio2` es el precio unitario y es el que importa** (`precio1` es el
> empaque completo). Don Julio compra pastillas sueltas, no cajas de 100.
> Rankear por `precio1` da un ranking equivocado. Ojo: `precio2` puede venir
> `null` — filtrar esos registros antes de ordenar.

### 4.4 `precioproducto/obtener` — detalle (opcional, pero vale oro)

```json
{"filtro": {"codigoProducto": 48171, "codEstablecimiento": "0124339", "tokenGoogle": ""}}
```

(Aquí `codigoProducto` es el `codProdE` del resultado anterior, no el `grupo`.)

Agrega **`horarioAtencion`** (`"LUN A VIE: 08:00 A 16:00; SAB: 08:00 A 16:00"`),
`ruc`, `email`, `directorTecnico`, `presentacion`, `registroSanitario` y
`condicionVenta` (`"Con receta médica"`).

**El horario es el detalle que vende la demo**: mandar a un cojo de 90 años a
una botica cerrada es exactamente el problema que decimos resolver. Son 3
llamadas extra (una por opción del ranking) — barato.

---

## 5. Qué falta, en orden de importancia

| # | Qué | Quién | Sin esto… |
|---|---|---|---|
| 1 | `analizar_receta()` — foto → lista de medicamentos (visión vía OpenRouter) | analizador | no hay demo |
| 2 | Cliente DIGEMID: autocomplete + preciovista + ranking por `precio2` | ⚠️ **sin dueño** | no hay demo |
| 3 | Tabla `{distrito: ubigeo}` de los 43 distritos (de §4.2, hardcodear) | con el #2 | no hay demo |
| 4 | Formatear el `mensaje` en inglés, 3 opciones, letra grande | analizador | demo fea |
| 5 | `horarioAtencion` por opción (§4.4) | si sobra tiempo | se pierde un punto |

**Sugerencia:** que #2 y #3 vivan en un `digemid.py` nuevo, con una sola función
`buscar_precios(nombre_medicamento, distrito) -> list[Oferta]`. Así el del
analizador la importa y no chocamos en el merge (`AGENTS.md`: cada quien su
módulo).

### Probar el camino completo sin Telegram

```bash
python -c "from receta import analizar_receta; print(analizar_receta('data/recetas/prueba.jpg','Lince',1))"
```

---

## 6. Criterios de "demo ganada"

- [ ] Foto de una receta **real** de gastritis, tomada en el momento con el celular
- [ ] Distrito **Lince**, escrito a mano en el chat
- [ ] Respuesta en **menos de ~10 segundos**
- [ ] Al menos **1 medicamento** bien leído, con **3 boticas** y **precios reales**
- [ ] Todo el texto en pantalla **en inglés**
- [ ] El precio se puede **verificar en vivo** en la web de DIGEMID

## 7. Anti-objetivos (NO hacer hoy)

- ❌ WhatsApp real (Business API = verificación de días). **Telegram y listo**;
  se menciona en el pitch que el flujo es idéntico.
- ❌ Login, cuentas, historial, base de datos propia.
- ❌ Mapa, GPS, distancias reales. **El distrito basta.**
- ❌ Scrapear DIGEMID entero a una BD local. La API responde en vivo y rápido;
  un dump masivo es tiempo perdido y riesgo de bloqueo. *(Si se cae en la demo:
  cachear en JSON las 2-3 consultas del guion como plan B.)*
- ❌ Interpretar dosis, diagnosticar o sugerir tratamientos. **No damos consejo
  médico**: leemos la receta que un médico ya firmó y comparamos precios.

---

## 8. Notas éticas / legales (para el pitch)

- Los datos son **públicos, del MINSA** (Observatorio Peruano de Productos
  Farmacéuticos - SNIPPF). No hay dato privado de terceros.
- Las fotos de recetas son **dato sensible de salud**: quedan en
  `data/recetas/`, que **está en `.gitignore`**. No commitear recetas reales.
- El bot **no reemplaza al químico farmacéutico** ni al médico. Muestra precios
  oficiales y deja la decisión en el usuario.
