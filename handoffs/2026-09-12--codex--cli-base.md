# Base del CLI para tres equipos

Se integra sobre ec70548 conservando bot.py, receta.py y digemid_dump.py intactos.
Un entrypoint stdlib: `python -m medisaving`. Ingesta, analytics y UX registran
subcomandos desde carpetas propias; no necesitan editar el dispatcher.

Entrega: contrato Offers/Ranking/Telegram v1, almacenamiento local privado por IDs,
import JSON normalizado, ranking comparable, render texto sin envío, fixture
sintético, tests de integración y CI Python 3.14. Ver README y docs/teams/.

Cada equipo crea su rama desde este commit y modifica únicamente sus carpetas y
su documento. Core/contrato/dispatcher son integración compartida: proponer cambios
en PR separado. Los tres documentos incluyen alcance, prioridades y criterios.

No hay integración nueva con el bot ni despliegue remoto. No se consultó DIGEMID
ni se enviaron mensajes para esta entrega. Conexión oficial, caché, canastas y
render visual están pendientes en sus equipos. La latencia aún no está medida.

El prototipo local anterior de Codex/Node se preservó en prototypes/codex-telegram/
sin incluirlo en este commit. Su servicio remoto no se modificó.

Validación: `python3 -m unittest discover -v` (7 casos; incluye pipeline por procesos).
