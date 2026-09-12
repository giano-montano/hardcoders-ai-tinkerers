# Contrato CLI v1

`python -m medisaving [--data-dir PATH] AREA COMMAND ...`

Cada módulo exporta `register(subparsers)` y asigna `args.run(args, store)`.
Ese handler devuelve un diccionario JSON serializable; no imprime datos ni logs
en stdout. Logs futuros a stderr. El dispatcher imprime un único JSON.
Éxito: `{"ok":true,"schema_version":1,"data":{...}}`, exit 0.
Error de datos/storage: `{"ok":false,"schema_version":1,"error":{"code":"INVALID_INPUT_OR_STORAGE","message":"..."}}`, exit 2.
Errores de sintaxis de argumentos usan argparse: stderr y exit 2; help es texto.

## Offers → Ranking → Telegram

El contrato ejecutable está en `medisaving/core.py`, con ejemplo completo en
`examples/offers.synthetic.json`. Todos los artefactos tienen `kind` y
`schema_version: 1`. IDs opacos hex de 32 caracteres; no pasar filas por prompts.
`Store.put` crea un archivo privado; el ID se entrega después de terminar de escribir.
No es un almacén multiusuario con autorización: el caller separa data-dir por chat.

Offers incluye `offers` y `source`:

- `source`: `name`, `fetched_at` (ISO 8601), `scope`, `complete` booleano explícito.
  Completo se refiere únicamente al alcance declarado; nunca implica todo Perú.
- Identidad requerida: `offer_id` único, `medicine_key` (principio activo normalizado),
  `medicine` (nombre comercial/producto), `strength`, `form`, `pharmacy_id`
  (sucursal, no cadena), `pharmacy`, `district`, `address`.
- `currency: PEN`; `unit_price_cents`, `pack_price_cents`: entero positivo o null.
  `pack_units`: entero positivo o null. No inferir unidad de precio de caja.
- `laboratory`, `presentation`, `phone`, `reported_at`: texto o null.
  Datos no disponibles se mantienen null; no inventar campos para pasar validación.
  Ofertas sin identidad/dirección suficiente se reportan como rechazadas por ingesta.

Ranking conserva `source`, `dataset_id`, `basis`, `filters`, `groups` y
`excluded_unpriced_or_unknown_pack`. Cada grupo incluye `medicine_key`, `strength`,
`form`, `pack_units` y `offers` seleccionadas intactas. Unidad agrupa sin pack_units;
caja exige unidades conocidas e iguales. Empates por pharmacy_id, offer_id.
Se elige una oferta por sucursal y grupo. No deduce disponibilidad ni sustitución.
El orden de v1 es solo precio reportado, no cantidad necesaria ni costo de traslado.

Telegram guarda `result_id`, `messages` (lista de texto plano), `parse_mode: null`.
No enviar HTML/Markdown por accidente. Renderizar no envía mensajes.

## Extensiones entre equipos

Ingesta devuelve `dataset_id`; analytics consume ese ID y devuelve `result_id`;
UX consume `result_id`. Datos crudos/cache pertenecen a ingesta y no llegan a UX.
Campos nuevos opcionales pueden proponerse manteniendo fixtures previos; cambios
de significado, nombre o obligatoriedad requieren coordinación/versionado.
No agregar React/dependencias sin acordarlo según AGENTS.md.

No guardar tokens, fotos, chat IDs o consultas reales en fixtures/logs/commits.
Cada equipo añade tests en su propia carpeta; la CI descubre todos automáticamente.
