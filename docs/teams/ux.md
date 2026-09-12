# Equipo UX — mismo CLI

Rama: `team/ux`. Propiedad: `medisaving/ux/`, `tests/ux/`, este documento y futura
skill `skills/ux/`. No editar ingesta, analytics, bot.py ni receta.py.

## Punto de partida

`python -m medisaving ux telegram RESULT_ID` devuelve mensajes de texto plano y
presentation_id. No envía mensajes. Leer `docs/cli-contract.md`.
La demo usa inglés según AGENTS.md; nombres propios se conservan.

## Trabajo prioritario

1. Afinar mensajes breves: medicamento exacto, farmacia/sucursal, distrito,
   dirección, laboratorio, unidad/caja y fecha. Indicar datos no reportados.
   Mostrar pocas opciones, permitir ampliar y no ocultar cobertura parcial.
2. Plantillas de conversación/progreso: foto ilegible, distrito faltante, consulta
   ambigua, sin resultados, error y recuperación. La interpretación la hace el
   agente; el CLI valida/renderiza estados explícitos, sin inventar respuestas.
3. Agregar render de imagen/PDF con plantilla fija, no código generado por consulta.
   Evaluar renderer y coordinar dependencias antes de introducir React u otra librería.
   Texto primero; generar archivos solo cuando aportan o el usuario los solicita.
4. Acordar con dueño del bot un adaptador separado para entrega, reintentos e
   idempotencia. Evitar envíos duplicados y mezcla de chats. No probar envíos reales
   desde tests; requerir destino autorizado para un smoke de entrega.
5. Skill breve para conversar y llamar al CLI: aclaraciones necesarias, cuándo usar
   cada plantilla, límites de datos y cómo entregar artefactos.

## Listo cuando

Consume Ranking v1 sin HTTP, sin recalcular precios ni modificar resultados.
Tests cubren vacío/parcial, unidad desconocida, textos largos y caracteres Telegram.
Inspeccionar render visual cuando exista. Medir tiempo hasta primer mensaje útil,
tiempo de render y tamaño de salida. No bloquear el texto esperando el PDF.

```bash
python -m unittest discover -s tests/ux -v
python -m unittest discover -v
```

Crear handoff propio. La integración de envío es un PR coordinado con el dueño de bot.py.
