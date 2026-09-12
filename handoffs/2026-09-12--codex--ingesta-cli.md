# Ingesta CLI implementada

Rama `team/ingesta`. Se trabajó exclusivamente en ingesta, sus pruebas, skill,
documentación y medición del flujo histórico. Analytics, UX, core y bot intactos.
No se desplegó ni reinició el servicio remoto, ni se envió Telegram.

Comandos: `python -m medisaving ingest u|r|f|d`. Ver
`docs/teams/ingesta.md` para sintaxis, resultados y evidencia del pitch.
`f UBIGEO ID...` devuelve un dataset Offers v1 por ID, conteo, cobertura y warnings;
no expone las filas al modelo. `d DATASET_ID OFFER_ID` obtiene detalle separado.

Incluye cliente HTTP stdlib, caché privado, reintentos acotados, normalización
Decimal, verificación de ubicación/concentración, paginación con totales y detección
de repetidos, resultados parciales y preservación de formas farmacéuticas reales.
No sustituye presentaciones: en clonazepam 0,25 mg la fuente mezcla sublingual y
desintegración oral. El consumidor debe seleccionar la forma que se pidió.

Skill breve en `skills/ingesta/SKILL.md`, validada con quick_validate.py. No se
instaló en el bot. Sin dependencias nuevas del CLI; solo benchmark opt-in usa
tiktoken temporal vía uv --no-project.

Validación: 16 tests de ingesta / 21 de compatibilidad pasaron; smoke contra fuente
oficial: 190 ofertas de tres grupos en Lince, cero rechazos. Fetch frío hizo 3 HTTP;
fetch caliente hizo 0. Ingesta + resolución + 3 detalles: 4,965 s frío, 0,336 s caliente.

Rollout existente: 2.940.806 input tokens acumulados en el turno, 2.864.512 cacheados,
5.804 output, 343,627 segundos. Ninguna nueva sesión LLM para la comparación.
Texto de herramientas con o200k_base: 71.126 → 870 tokens (98,78% menos); no es
comparación de facturación ni reducción E2E medida. Evidencia agregada en
`tests/ingest/benchmark-result.json`; reproducción en `tests/ingest/benchmark.py`.
Rollout original privado permanece bajo data/local ignorado por Git.
