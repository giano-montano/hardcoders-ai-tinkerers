# Telegram + Codex runtime

Runtime activo en laptop: `/home/f3mt0/medicinas-telegram`, servicio de usuario
`medisaving.service`. Este prototipo existía antes del CLI; se versiona ahora junto
con su integración. El bot Python de la raíz pertenece a otro flujo y no se modifica.

`src/bot.js` conserva polling, cola por chat y entrega. `src/codex.js` monta el CLI
como solo lectura en `/opt/medisaving`, y el workspace privado en `/work`.
El comando `med` usa `/work/ingest` para los datos. Las instrucciones de ingesta se
inyectan en la configuración de Codex y el prompt de cada turno, también al reanudar
conversaciones. Playwright queda disponible para documentos y ya no es requerido
para iniciar el agente. Las búsquedas de medicamentos usan el CLI.

Configuración pública en `.env.example`; token solo en `.env` remoto, nunca en Git.
No copiar el directorio `data/`: contiene conversaciones, imágenes y auth de sesiones.
`MEDISAVING_CLI_DIR` puede señalar un release; por defecto se usa `./cli`.

## Distribución de release

El directorio `cli/` contiene el paquete `medisaving/`, `skills/ingesta/` y `bin/med`
(copiado desde `medisaving/ingest/runtime/bin/med`). Sin dependencias Python nuevas.
El runtime usa Python 3.12 del host, verificado por smoke; desarrollo/CI usan 3.14.
Node y dependencias de Playwright existentes se conservan.

Preparar el release fuera del directorio activo, verificarlo y después activar:

```bash
node CLI_RELEASE/medisaving/ingest/runtime/smoke.mjs RUNTIME_RELEASE
```

Requiere Linux/bwrap y los mismos recursos de navegador del runtime. La prueba
llama exclusivamente al CLI en el sandbox real: fuente pública, caché, montajes y
lectura de ofertas/detalles. No ejecuta Codex ni conecta Telegram.

Release activado el 2026-09-12: `releases/ingest-integration-20260912`.
Respaldo previo: `releases/pre-ingest-integration-20260912` con codex.js, agent.md
y destino anterior del enlace CLI en rollback.json. Para revertir, drenar la cola,
detener servicio, restaurar esos archivos/enlace y volver a iniciarlo.

## Alcance actual

`med u/r/f/v/d` integra solo ingesta. `v` lee 1–5 ofertas de un producto en orden
de fuente, con forma exacta opcional; no ordena precios ni calcula canastas.
El agente debe presentar opciones verificadas, no afirmar que son las más baratas.
La integración de analytics y su medición E2E quedan pendientes.
No se ejecutó una sesión nueva del modelo para probar esta activación. La próxima
consulta real permitirá verificar el uso efectivo del CLI por el agente.
