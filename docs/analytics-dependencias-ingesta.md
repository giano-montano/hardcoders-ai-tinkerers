# Dependencias analytics ↔ ingesta

Análisis de acoplamiento entre `docs/teams/analytics.md` y `docs/teams/ingesta.md`
sobre el contrato compartido (`docs/cli-contract.md`, `medisaving/core.py`).
Escrito inicialmente contra `main`, donde solo existía `ingest import`. Un
`git pull` posterior trajo `origin/team/ingesta` (commit `3edf3b5`, sin fusionar
a `main`) con `ingest resolve/fetch/detail` implementados de verdad
(`medisaving/ingest/normalize.py`, `commands.py`, `client.py`). Las secciones
marcadas **[confirmado en team/ingesta]** vienen de leer ese código, no de
inferencia sobre el plan.

## Dependencias directas

1. **`dataset_id` como única vía de entrada.** `ingest import` guarda el dataset
   con `Store.put` y devuelve `dataset_id`; `analytics rank` solo puede leerlo
   con `Store.get(dataset_id, "offers")` desde el mismo `--data-dir`. Analytics
   no tiene forma de recibir filas fuera de ese mecanismo.
2. **Forma exacta de Offers v1.** `analytics rank` agrupa por
   `(medicine_key, strength, form, pack_units)` usando *string match* exacto
   (ver `medisaving/analytics/__init__.py:29-31` y el test
   `test_strength_form_and_pack_size_are_not_mixed`). Depende de que ingesta
   normalice esos campos de forma consistente antes de guardarlos.
3. **Enteros en céntimos, nunca floats.** `core.validate_dataset` exige
   `unit_price_cents`/`pack_price_cents`/`pack_units` como entero positivo o
   `null`. La tarea 3 de ingesta ("usar Decimal para convertir a céntimos") es
   la que garantiza esto; analytics no vuelve a validar la conversión, solo el
   tipo.
4. **`pack_units` null cuando es ambiguo.** El `--basis pack` de analytics
   excluye filas con `pack_units` o `pack_price_cents` nulos
   (`excluded_unpriced_or_unknown_pack`). Si ingesta infiere un valor en vez de
   dejarlo `null` (prohibido por su propio punto 3: "No inferir campos
   desconocidos"), analytics agruparía cajas de tamaño distinto como si fueran
   comparables.
5. **`pharmacy_id` a nivel de sucursal, no cadena.** Analytics selecciona una
   oferta por `pharmacy_id` y grupo para diversificar sucursales. El criterio
   "listo cuando" de analytics ("jamás declarar que una farmacia tiene todas
   las medicinas por compartir nombre de cadena") depende de que ingesta mapee
   `codEstab` a sucursal real, no a cadena.
6. **`source.complete` y `source.scope` se propagan intactos.** Analytics copia
   `dataset["source"]` completo al resultado de ranking sin reinterpretarlo.
   Si ingesta marca `complete=false` por páginas fallidas (fetch con
   reintentos/backoff), ese matiz llega a UX solo como booleano; no hay campo
   para "cobertura parcial explicada" que analytics pueda usar en resúmenes.
7. **Un solo `dataset_id` por invocación de `rank`.** El CLI actual
   (`analytics rank DATASET_ID`) no acepta múltiples IDs. Si ingesta cachea
   resultados de `fetch` como artefactos separados por consulta, alguien debe
   fusionarlos en un único dataset antes de que analytics pueda rankear sobre
   todos a la vez (relevante para la tarea 2 de analytics: canasta multi-sucursal).
8. **Fixture compartido.** `examples/offers.synthetic.json` alimenta tests de
   ambos equipos (`tests/analytics/test_rank.py`, `tests/helpers.py`). Un
   cambio de forma en ingesta sin actualizar el fixture rompe tests de
   analytics que no tocaron ese archivo.

## Riesgos concretos al integrarse

- **Formato de `strength` ya diverge entre fixture y datos reales
  [confirmado].** `normalize.strength()` en la rama de ingesta produce
  `"20mg"` (sin espacio, minúscula, coma→punto): ver los ejemplos reales
  `ingest r escitalopram 20mg` y `ingest f 150116 1515:3:20mg`. El fixture
  compartido `examples/offers.synthetic.json` (usado por
  `tests/analytics/test_rank.py`) usa `"20 mg"` con espacio. Analytics agrupa
  por *string match* exacto de `strength`, así que esto no rompe su lógica,
  pero significa que el vocabulario "canónico" nunca se acordó explícitamente
  entre equipos — cualquier prueba de integración que mezcle el fixture
  antiguo con datos reales de `fetch` tratará el mismo medicamento como dos
  grupos distintos si los formatos no coinciden en algún punto.
- **`medicine_key` no pasa por ninguna normalización [confirmado].** A
  diferencia de `strength`, `normalize.offer()` asigna
  `medicine_key = row.get("nombreSustancia")` tal cual (solo `.strip()`), o
  cae a `f"digemid:{group}"` cuando falta el nombre de sustancia
  (`medisaving/ingest/normalize.py`). Si DIGEMID devuelve mayúsculas/minúsculas
  distintas entre consultas, o si algunos productos no tienen sustancia y caen
  al formato `digemid:1515`, analytics fragmenta el agrupamiento o muestra
  claves no legibles en resúmenes (tarea 5 de analytics: "interpretar
  parciales").
- **Campos nuevos no listados en el contrato v1 [confirmado].** La rama de
  ingesta agrega a cada oferta `source_product_id`, `source_group`,
  `source_form_group`, `ubigeo`, y a `source` un array `coverage`
  (`commands.py: fetch`). `docs/cli-contract.md` exige proponer primero los
  campos nuevos como cambio compartido; aquí ya están implementados y
  commiteados en la rama sin que conste una propuesta separada. No rompen a
  analytics (que ignora campos desconocidos), pero divergen del contrato
  documentado tal como está escrito hoy.
- **Múltiples formas bajo el mismo grupo/concentración — funciona, pero es un
  caso real ya observado [confirmado].** El hallazgo de la rama de ingesta:
  clonazepam 0,25 mg trae 23 ofertas "Tableta Sublingual" y 14 "Tableta de
  Desintegración Oral" bajo el mismo `source_group`+`strength`, marcado con el
  warning `verify_offer_forms`. Ingesta las conserva separadas por `form`, así
  que analytics no las mezclará (su agrupación incluye `form`) — esto valida
  que el diseño es correcto, pero confirma que analytics debe mostrar la forma
  en cualquier resumen compacto, no asumir que concentración implica forma
  única.
- **`source.complete` es cobertura de la consulta, no de stock/equivalencia
  clínica [confirmado, ya documentado por ingesta].** El propio doc de ingesta
  aclara: "Complete significa cobertura de los grupos/ubigeo solicitados, no
  equivalencia clínica ni stock confirmado." Analytics reenvía `source` intacto
  al resultado de ranking; si la skill de analytics (tarea 5) o UX interpretan
  `complete: true` como "tenemos todo el catálogo", estarían malinterpretando
  el campo. La cobertura por producto vive en `source.coverage`, que analytics
  hoy no lee ni resume — lo reenvía sin usarlo.
- **Sin test de integración `fetch → rank` todavía.** La rama de ingesta no
  toca `tests/integration/test_pipeline.py`; sus "Listo cuando" (import → rank
  → telegram) siguen probados solo con el flujo `import` viejo. No hay
  evidencia automatizada de que la salida real de `ingest fetch` (con los
  campos nuevos y el `strength` sin espacios) pase limpiamente por
  `analytics rank` tal como está hoy.
- **Redondeo ya no es un riesgo abierto [confirmado, mitigado].** `normalize.
  positive()` usa `Decimal` y exige valor entero exacto tras multiplicar por
  100, lanzando error en vez de redondear silenciosamente. Esto cierra el
  riesgo que se había anticipado sobre conversión float→céntimos.
- **Desalineación de `--data-dir` entre procesos.** Si ingesta y analytics se
  invocan en procesos/entornos distintos sin compartir explícitamente
  `--data-dir`, `store.get(dataset_id, ...)` falla con `INVALID_INPUT_OR_STORAGE`
  aunque el dataset exista. Confirmado que ambos comandos toman el mismo
  `Store(args.data_dir)` desde `medisaving/__main__.py`, así que basta con
  pasar el mismo `--data-dir` en ambas invocaciones.
- **Un solo `dataset_id` por invocación de `rank`.** `ingest fetch` ya produce
  un `dataset_id` por llamada (hasta 10 productos combinados en un solo
  dataset), lo cual cubre el caso de "varios medicamentos, un distrito". Pero
  comparar el mismo medicamento entre *distritos* o *fetches* distintos
  todavía requeriría fusionar datasets antes de rankear, y no hay comando para
  eso en ninguna de las dos ramas.

## Qué puede avanzar en paralelo sin bloquearse

- Analytics puede seguir desarrollando ranking/canasta/benchmark de rendimiento
  usando `ingest import` + fixtures sintéticos existentes; no depende de que
  `ingest resolve`/`fetch` estén implementados todavía (ninguno de los dos
  existe aún en `medisaving/ingest/__init__.py`, que solo registra `import`).
- Ingesta puede construir `resolve`/`fetch`/caché sin esperar a analytics,
  siempre que respete el contrato Offers v1 vigente y no cambie el significado
  de campos sin proponerlo antes.

## Recomendación

`team/ingesta` (commit `3edf3b5`) ya implementó `resolve`/`fetch`/`detail` sin
que conste coordinación previa sobre dos puntos que el contrato exige acordar:

1. **Normalizar `medicine_key`** igual que ya se normaliza `strength`
   (`normalize.strength()`), o documentar explícitamente que analytics debe
   tolerar variaciones de mayúsculas/minúsculas y claves `digemid:*` sin
   sustancia. Hoy no hay acuerdo ni test que lo cubra.
2. **Decidir si los campos nuevos** (`source_product_id`, `source_group`,
   `source_form_group`, `ubigeo`, `source.coverage`) se documentan como
   extensión oficial de Offers v1 en `docs/cli-contract.md`, tal como pide
   "Campos nuevos opcionales pueden proponerse manteniendo fixtures previos."
   Ahora mismo existen en el código pero no en el contrato escrito.

Antes de fusionar `team/ingesta` a `main`, agregar un test de integración que
alimente `analytics rank` con la salida real de `ingest fetch` (no solo con el
fixture sintético), para detectar a tiempo cualquier fragmentación de grupos
por formato de `strength`/`medicine_key`.
