# Equipo ingesta — mismo CLI

Rama: `team/ingesta`. Propiedad: `medisaving/ingest/`, `tests/ingest/`,
este documento y futura skill `skills/ingesta/`. No editar analytics, UX o bot.

## Punto de partida

`python -m medisaving ingest import examples/offers.synthetic.json` valida y guarda
el contrato Offers v1. Devuelve dataset_id y conteo, no miles de filas.
Leer `docs/cli-contract.md` y revisar `digemid_dump.py` / `HAPPY_PATH.md` como
referencias del cliente existente. No modificar el descargador compartido sin coordinar.

## Trabajo prioritario

1. Agregar `ingest resolve` para buscar catálogo local y devolver candidatos compactos.
   Resolver principio activo, concentración y forma; si son ambiguos, devolverlos
   explícitamente para que el agente pregunte. No convertir SL a tableta oral.
2. Agregar `ingest fetch` por producto y ubigeo usando acceso oficial permitido:
   timeout, paginación acotada, reintentos con backoff y límite de concurrencia.
   No descargar todo el país en una consulta interactiva.
3. Normalizar respuestas a Offers v1. Guardar raw separado; mapear codEstab a sucursal;
   verificar precio1/2, fracciones, presentación y laboratorio contra la fuente.
   Usar Decimal para convertir a céntimos, no floats. No inferir campos desconocidos.
4. Caché por consulta normalizada con TTL y fetched_at, cobertura explícita y
   resultados parciales ante páginas fallidas. Reutilizar consultas idénticas.
5. Skill breve: comandos, resolución ambigua, errores, caché y ejemplos de IDs.

## Listo cuando

Datos de fixtures oficiales anonimizados recorren import → rank → telegram sin
modificar otros módulos. Tests cubren páginas repetidas, parciales, vacías, timeout,
dinero ambiguo y forma/dosis. Medir consulta fría y caliente, requests y bytes de
stdout. Red real solo en smoke opcional, nunca requerida por CI.

```bash
python -m unittest discover -s tests/ingest -v
python -m unittest discover -v
```

Crear handoff propio. Si faltan campos en v1, proponer primero el cambio compartido.

## Evidencia para el pitch — medición histórica, 2026-09-12

Consulta real ya completada: tres medicamentos, un distrito. Se inspeccionó el
rollout existente; **no se abrió una nueva sesión del modelo para medirla**.
Los logs privados permanecen fuera de Git en `data/local/ingest-audit/`.

| Métrica | Consulta de medicamentos |
| --- | ---: |
| Inicio del turno | 2026-09-12 13:35:06.233, Lima |
| Fin del turno | 2026-09-12 13:40:49.860, Lima |
| Duración del turno | 343,627 s (5 min 44 s) |
| Tokens de entrada acumulados | 2.940.806 |
| De esos, entrada en caché | 2.864.512 |
| Entrada no cacheada | 76.294 |
| Tokens de salida | 5.804 |
| Llamadas de herramientas del agente | 40 (33 custom calls + 7 waits) |

Método: diferencia entre `total_token_usage` del último `token_count` anterior
al turno y el último de la sesión. Contadores previos: entrada 70.189, caché
44.672, salida 238. Finales: entrada 3.010.995, caché 2.909.184, salida 6.042.
La duración proviene de `task_started` y `task_complete`, no del tiempo de entrega
de Telegram. Las 40 llamadas son invocaciones del agente; algunas contienen varias
operaciones de navegador, por lo que no equivalen a 40 requests HTTP.

**Lectura correcta:** tokens acumulados de múltiples pasos, no un contexto de
2,94 millones de tokens ni 2,94 millones de tokens cobrados a tarifa sin caché.
Incluye interpretación y respuesta final; no atribuir todo exclusivamente a ingesta.

Flujo observado: búsquedas por nombre/marca, selección repetida de ubicación,
snapshots de tablas, corrección del formulario y apertura de detalles por producto.
Validación HTTP posterior: el endpoint oficial responde directamente; una consulta
de precios devolvió 122 filas pese a `tamanio: 50`. El genérico ARIPIPRAZOL no
devolvió candidatos; el flujo previo resolvió mediante marca. CLONAZEPAM devolvió
0,5 y 2 mg; ZATRIX incluyó ZATRIX SL 0,25 mg. Son observaciones de esta fecha,
no garantías permanentes de la API ni equivalencias clínicas generales.

Frase sustentada para pitch: «En una consulta real de tres medicamentos, el agente
tardó casi seis minutos y acumuló 2,94 millones de tokens de entrada repitiendo
operaciones de navegador; estamos convirtiendo esas operaciones en comandos
deterministas que entregan resultados compactos».

## Feature implementado y benchmark del CLI

Rama `team/ingesta`. Solo se modificó ingesta, sus pruebas, esta documentación,
la skill `skills/ingesta/SKILL.md` y su handoff. No se integró ni desplegó el bot.

```bash
python -m medisaving ingest u lince
python -m medisaving ingest r escitalopram 20mg
python -m medisaving ingest r aripiprazol 5mg
python -m medisaving ingest r clonazepam 0.25mg --sl
python -m medisaving ingest f 150116 1515:3:20mg 449:3:5mg 1058:3:0.25mg
python -m medisaving ingest d DATASET_ID OFFER_ID
```

`u` resuelve distrito; `r` devuelve candidatos compactos con IDs del servidor;
`f` consulta varios productos, normaliza y guarda Offers v1; `d` obtiene un detalle
por ID de oferta. También existen los nombres resolve/fetch/detail. No hay ranking.
Para diagnóstico: `f --stats`; refresco explícito: `r/f/d --fresh`.
Se consulta autocomplete con caché, en vez de depender del catálogo local que
conserva solo un nombre por grupo y puede omitir nombres genéricos.

Precios y detalle: TTL 15 minutos; candidatos y distritos: 24 horas. Cache privado
en el data-dir del caller; cada request tiene timeout de 15 s, hasta dos reintentos
para errores transitorios y pausa mínima de 0,4 s entre requests. 403 no se reintenta.
Fetch limita a diez productos y tres páginas por producto por defecto (`--pages`
permite 1–20). No hay consultas nacionales implícitas ni sesiones de navegador.

El dato crudo queda en caché; las ofertas conservan código de sucursal/producto,
concentración, forma exacta de la fuente, laboratorio, dirección, teléfono, fecha,
fracciones y precios independientes convertidos con Decimal. Presentación ausente
queda null; `d` la obtiene del detalle junto con registro y condición de venta.
El detalle se guarda separado y no sobrescribe precios del dataset.

La respuesta de fetch en el caso medido ocupa **158 bytes / 59 tokens o200k_base**:
solo dataset_id, n=190, complete=true y warning de formas distintas dentro del grupo.
Complete significa cobertura de los grupos/ubigeo solicitados, no equivalencia
clínica ni stock confirmado. Se verifican totales, páginas repetidas, duplicados,
ubicación y concentración. Errores/rechazos conservan resultados parciales explícitos.

Hallazgo de la fuente: clonazepam 0,25 mg devolvió 23 ofertas de Tableta Sublingual
y 14 de Tableta de Desintegración Oral. Se conservan ambas formas con
`verify_offer_forms`; el consumidor debe seleccionar la forma solicitada. No
interpretar familia «Tableta - Capsula» o la marca SL como prueba de todas las filas.

### Comparación medida, sin nueva sesión LLM

| Métrica | Navegador histórico | CLI frío | CLI caliente |
| --- | ---: | ---: | ---: |
| Texto devuelto por herramientas, bytes | 225.353 | 2.281 | 2.278 |
| Ese texto tokenizado con o200k_base | 71.126 | 870 | 878 |
| Invocaciones | 40 herramientas (incluye waits) | 8 comandos | 8 comandos |
| Tiempo | 343,627 s, turno completo | 4,965 s, adquisición | 0,336 s, adquisición |
| Ofertas normalizadas por CLI | No medido | 190 | 190 |
| HTTP de fetch de los tres grupos | No medido | 3 | 0 (3 hits) |

CLI frío/caliente ejecutan distrito, tres resoluciones, fetch y tres detalles
(primera fila de fuente por grupo; no selección por precio). Se incluye arranque
de ocho procesos Python y stdout completo, incluso `--stats`. Cache frío en
directorio temporal nuevo; caliente usa el mismo directorio. Tiempos son una
muestra de cada caso, no percentiles ni SLA. IDs aleatorios varían algunos tokens.

**Resultado defendible para pitch: 98,78% menos tokens en el texto de resultados
de herramientas en este ensayo** (71.126 → 870), medidos con el mismo tokenizador.
Es una métrica de volumen de contexto; o200k_base es un comparador común, no una
afirmación del tokenizador exacto de Codex. No compara facturación ni el consumo
total acumulado de entrada del modelo contra una sola salida de CLI.

La ingesta determinista realizó cero llamadas LLM. No se midió una nueva sesión
del agente con CLI, por instrucción del usuario. Interpretar receta, conversar,
seleccionar resultados y enviarlos siguen fuera del benchmark. El navegador
histórico corrió en laptop Linux; el benchmark CLI en Mac Python 3.14. No anunciar
«E2E de 6 minutos a 5 segundos» ni inferir ahorro monetario de esos tiempos.

Artefacto agregado sin prompts: `tests/ingest/benchmark-result.json`. Reproducción:

```bash
uv run --no-project --with tiktoken python tests/ingest/benchmark.py \
  --rollout RUTA_PRIVADA_JSONL --output data/local/comparison.json
```

Ese script hace lecturas reales acotadas a la fuente, no abre Codex ni Telegram.
`tiktoken` es una dependencia temporal solo del benchmark, no del CLI ni de CI.
Los logs originales y fotos no se commitean. Tests offline: 16 de ingesta;
suite completa de compatibilidad: 21, todos pasaron.
