# Handoff — Bot de Telegram de recetas médicas

**Fecha:** 2026-09-12
**De:** Giano (bot de Telegram)
**Para:** el resto del equipo (quien toma el analizador de recetas)
**Estado:** bot funcionando de punta a punta con el analizador en stub.

---

## Qué está hecho

Un bot de Telegram en Python puro (stdlib, **sin `pip install`**) que hace este flujo:

| Paso | Qué pasa | Dónde está en el código |
|---|---|---|
| 1 | Primer mensaje o `/start` → pregunta el **distrito de Lima** | `bot.py` → `MSG_DISTRITO`, paso `PEDIR_DISTRITO` |
| 2 | Valida el distrito contra los 43 de Lima Metropolitana (sin tildes, mayúsculas y alias tipo `sjl`, `surco`) | `bot.py` → `buscar_distrito()` |
| 3 | Pide una **foto de la receta médica** | `bot.py` → `MSG_PEDIR_FOTO`, paso `PEDIR_FOTO` |
| 4 | Descarga la foto en `data/recetas/<chat_id>_<message_id>.jpg` | `bot.py` → `descargar_foto()` |
| 5 | **Llama a `analizar_receta()`** y le manda al usuario lo que devuelva | `bot.py` → `manejar()`, final |

> **Lee `AGENTS.md` antes de tocar nada.** Regla clave: todo texto que ve el
> usuario va en **inglés** (es lo que se proyecta en la demo); el código y los
> comentarios se quedan en español.

Archivos:

- `AGENTS.md` — convenciones del repo (idioma, stack, secretos).
- `bot.py` — el bot (long polling, ~200 líneas).
- `receta.py` — **el stub que hay que implementar.** Contrato ya definido con tipos.
- `.env` → `TELEGRAM_BOT_TOKEN=` (el token de BotFather; `.env` está en `.gitignore`).

Correr:

```bash
python bot.py
```

---

## 🚧 Lo que falta — ESTO ES LO QUE HAY QUE HACER

Implementar **una sola función**, en `receta.py`:

```python
def analizar_receta(ruta_imagen: str, distrito: str, chat_id: int) -> ResultadoReceta:
```

**Entrada:**
- `ruta_imagen` — ruta local a un `.jpg` ya descargado (ej. `data/recetas/12345_67.jpg`). Ya existe en disco cuando te llaman.
- `distrito` — distrito de Lima ya validado y normalizado (ej. `"Santiago de Surco"`). Sirve para buscar stock/farmacias cerca.
- `chat_id` — id del chat de Telegram, para trazabilidad.

**Salida** (`ResultadoReceta`, TypedDict ya declarado en `receta.py`):

```python
{
  "ok": True,                      # False si la imagen no es legible o no es una receta
  "medicamentos": [                # lista de Medicamento
      {"nombre": "Paracetamol",
       "presentacion": "500 mg tabletas",
       "dosis": "1 tableta cada 8 horas",
       "duracion": "5 días",
       "cantidad": "15 tabletas"},
  ],
  "texto_crudo": "...",            # OCR/transcripción completa, para depurar
  "mensaje": "texto que el bot le manda al usuario tal cual",
}
```

**Reglas del contrato:**
- ⚠️ **`mensaje` va EN INGLÉS.** Es lo que se proyecta en la demo. Si lo generas con un LLM, pide la respuesta en inglés en el prompt (no traduzcas después). Ver `AGENTS.md`.
- `mensaje` es lo único que ve el usuario en Telegram. Sale con `parse_mode="Markdown"`, así que `*negrita*` funciona — pero ojo con `_` y `*` sueltos en nombres de medicamentos.
- Si algo falla, devolver `ok=False` con un `mensaje` explicativo. **No lanzar excepción** (el bot la captura, pero el mensaje al usuario sale genérico y feo).
- La función es síncrona y bloquea el polling del bot. Si tarda >~30 s, avísame y lo paso a un hilo.

**Sugerencia de implementación** (hackathon, ir rápido): visión con OpenRouter, que ya está configurado en `.env` (`OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL=anthropic/claude-sonnet-5`). Mandar la imagen en base64 al endpoint compatible con OpenAI y pedir JSON estructurado con el shape de `Medicamento`.

---

## Cómo probar sin tocar Telegram

```bash
python -c "from receta import analizar_receta; print(analizar_receta('data/recetas/prueba.jpg','Miraflores',1))"
```

Pon cualquier foto de receta en `data/recetas/prueba.jpg`. Si eso devuelve el dict bien formado, el bot ya funciona completo.

---

## Decisiones / deuda conocida (por si alguien la quiere levantar)

- **Estado en memoria** (`ESTADO` en `bot.py`): se pierde al reiniciar el proceso. A propósito, es un hackathon. Si hace falta persistirlo → SQLite, media hora.
- **Un solo proceso con long polling.** No escala a varias instancias; no correr dos `python bot.py` con el mismo token a la vez (Telegram devuelve 409).
- **Sin webhook** — no hace falta ngrok ni hosting público.
- Después de analizar una receta, el bot se queda en `PEDIR_FOTO`: puedes mandar otra foto sin repetir el distrito. `/start` reinicia todo.
- Las fotos se guardan sin borrar en `data/recetas/`, que ya está en `.gitignore` (dato sensible de salud: no commitear recetas reales).

---

## Punto de contacto

El que tomó el analizador: toca solo `receta.py`. Si necesitas cambiar el contrato (más campos, respuesta async, mandar imágenes de vuelta), avísame y ajusto `bot.py` — no edites `manejar()` en paralelo o chocamos en el merge.
