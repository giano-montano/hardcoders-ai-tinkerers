---
name: ingesta
description: Consultar DIGEMID mediante el CLI medisaving para resolver productos y distritos, descargar ofertas y obtener detalles. Usar para ingesta de medicamentos; no calcula rankings ni canastas.
---

Desde la raíz del repo, usar `python -m medisaving ingest` (abreviado aquí como `I`).
El servicio elige `--data-dir` antes de `ingest` para aislar cada chat.

```text
I u lince
I r escitalopram 20mg
I r aripiprazol 5mg
I r clonazepam 0.25mg --sl
I f 150116 1515:3:20mg 449:3:5mg 1058:3:0.25mg
I d DATASET_ID OFFER_ID
```

`r` devuelve [ID, nombre, familia farmacéutica]. Elegir concentración exacta;
si quedan candidatos ambiguos, pedir precisión. Alias de búsqueda de aripiprazol
y clonazepam son pistas del portal, no sustituciones clínicas. `--sl` filtra el
nombre del candidato; la forma real queda en cada oferta y debe verificarse.

`f` consulta un distrito y hasta diez IDs en una llamada de CLI. Devuelve dataset_id,
n y complete, sin filas. Pasar el ID al módulo consumidor; no abrir el JSON completo
ni enumerar ofertas en el contexto. `d` obtiene el detalle de una oferta identificada
por el consumidor. Conserva precios de unidad y caja independientes, sin dividirlos.

Caché automática: precios/detalles 15 min, candidatos/distritos 24 h. `--fresh`
en r/f/d refresca; `f --stats` muestra requests, hits y duración solo para diagnóstico.
`u --province 1501` limita búsqueda a esa provincia (Lima por defecto).

Si complete=false, comunicar cobertura parcial; si hay warnings, explicar el motivo
sin asumir que todos significan descarga incompleta. No repetir comandos
idénticos esperando cubrir una página fallida: revisar con --fresh si corresponde.
403 no se reintenta; no intentar sortear el bloqueo con navegador. El CLI no llama
a un LLM, no envía Telegram y no interpreta fotos. No inventar dosis/formas faltantes.

Import y fetch producen `source.normalization: text-v1`: sustancia/forma en
minúsculas y espacios normalizados, concentración sin espacios ni ceros decimales
redundantes. Conservan textos originales en source_values y warnings en source.
`verify_offer_forms` pide comprobar forma; por sí solo no significa descarga parcial.
`diagnostics_unavailable` señala diagnóstico histórico desconocido en un import.
Con identity_status=source_group_only no confirmar coincidencia de sustancia.
No unir sales, sinónimos ni unidades distintas por intuición. Datos antiguos sin
perfil necesitan reimportación explícita antes de mezclarse con los nuevos; el CLI
no migra artefactos guardados automáticamente.
