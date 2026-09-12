# AGENTS.md — convenciones del proyecto

Para agentes y humanos que trabajen en este repo (hackathon AI Tinkerers).

## 🗣️ Idioma: TODO lo que se ve en la demo va en INGLÉS

Regla dura, no negociable: **cualquier texto que el jurado pueda ver proyectado
durante la demo está en inglés.** Eso incluye:

- Mensajes del bot de Telegram al usuario (`MSG_*` en `bot.py`).
- El campo `mensaje` que devuelve `analizar_receta()` en `receta.py`.
- Cualquier salida de un LLM que llegue al usuario → **pedir la respuesta en
  inglés en el prompt**, no traducir después.
- Botones, menús, comandos, descripciones del bot en BotFather.
- Mensajes de error visibles para el usuario.
- Títulos, labels y ejes de cualquier UI o gráfico que se proyecte.

**Qué SÍ se queda en español** (nadie lo proyecta):

- Comentarios y docstrings del código.
- Nombres de variables y funciones (`manejar`, `buscar_distrito`, `ESTADO`…).
- Los handoffs en `handoffs/`, este archivo, y los `.env*`.
- Logs de consola (`print(...)` del servidor).

**Excepción:** los nombres propios de distritos de Lima se quedan como son
(`Miraflores`, `Villa El Salvador`, `Jesús María`) — son topónimos, no se
traducen.

Regla mental rápida: *si sale en la pantalla del celular durante la demo → inglés.
Si solo lo ve el que programa → español.*

## Stack

- Python 3.14, **stdlib pura**. No agregar dependencias sin avisar al equipo —
  en la demo no queremos un `pip install` fallando.
- Secretos en `.env` (ya en `.gitignore`). Nunca hardcodear tokens ni keys.
- LLM vía OpenRouter, config en `.env` (`OPENROUTER_*`). Modelo por defecto:
  `anthropic/claude-sonnet-5`.

## Convenciones

- Un handoff por entrega en `handoffs/`, con formato `YYYY-MM-DD--<autor>--<tema>.md`.
- Las fotos de recetas van a `data/recetas/` y **no se commitean** (dato sensible
  de salud, ya está en `.gitignore`).
- Cada quien toca su módulo: `bot.py` es de Giano, `receta.py` del analizador.
  Si hay que cambiar el contrato entre ambos, se avisa antes de editar.
