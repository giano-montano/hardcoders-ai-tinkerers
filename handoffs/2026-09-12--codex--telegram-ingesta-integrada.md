# Ingesta integrada en el runtime Telegram existente

Activada en laptop el 2026-09-12 a las 15:04:28 Lima. Servicio `medisaving.service`.
Release: `/home/f3mt0/medicinas-telegram/releases/ingest-integration-20260912`.
Respaldo: `releases/pre-ingest-integration-20260912` en el mismo directorio base.

Se versiona el prototipo Node existente bajo `prototypes/codex-telegram/`.
Su receptor `src/bot.js` se conserva; cambian el montaje de CLI en `src/codex.js`
y las instrucciones de búsqueda en agent.md. El bot Python de main no se modifica.
El código CLI queda de solo lectura, datos por chat en /work/ingest, comando med.
Instrucciones de ingesta por turno y developer_instructions; navegador opcional
para documentos. Referencia de configuración:
https://developers.openai.com/codex/config-reference/

Se añadió `ingest v DATASET_ID PRODUCT_ID`: lectura de 1–5 ofertas en orden de
fuente, filtro exacto de forma y paginación. No calcula ni ordena precios. Las
respuestas del agente deben decir opciones verificadas, no las más baratas.
Analytics permanece sin cambios y no está integrado en este recorrido.

Pruebas: 30 tests Python, sintaxis Node, config TOML generada válida y smoke en
el mismo constructor bwrap que utiliza runAgent. Obtuvo 190 ofertas y 3 detalles;
fetch caliente con cero HTTP. Verificó montaje de solo lectura, aislamiento de
otro chat y que el token del bot no es visible. Cero sesiones LLM nuevas y cero
envíos de prueba a Telegram. No afirmar que se probó una respuesta E2E del agente.

## Incidencia pendiente: segundo receptor del mismo bot

El servicio está activo, pero recibe 409 por getUpdates concurrente. Primer 409
observado: 15:03:50 Lima, anterior a la activación de esta versión. Nuestro smoke
no conecta Telegram. En laptop se identificó un solo proceso receptor y una sola
conexión TCP a api.telegram.org: servicio activo, PID 732880 en esa inspección.
En Mac no se detectó conexión a api.telegram.org; los procesos relevantes eran
Codex/herramientas, no otro bot. No se identificó el segundo receptor en las dos
máquinas revisadas. Esto no prueba ausencia absoluta de procesos intermitentes.
No se detuvieron procesos ajenos, ni se rotó el token, ni se cambió webhook.

La recepción fiable queda pendiente de localizar/detener el consumidor concurrente
o acordar un bot separado. No iniciar otro getUpdates para diagnosticarlo.
