# Telegram + Codex runtime

Runtime activo en laptop: `/home/f3mt0/medicinas-telegram`, servicio de usuario
`medisaving.service`. Este prototipo existía antes del CLI; se versiona ahora junto
con su integración. El bot Python de la raíz pertenece a otro flujo y no se modifica.

Bot activo desde 2026-09-12 15:14 Lima: **@MedSavings_bot**. Cola y datos privados
en `data-medsavings/` mediante DATA_DIR. Los datos del bot anterior siguen en data/;
no se reusan sus offsets ni se reenvían sus trabajos al bot nuevo.

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

Release actual: `releases/full-flow-20260912` (ingesta + analytics + UX).
Respaldo previo: `releases/pre-full-flow-20260912` con codex.js, agent.md
y destino anterior del enlace CLI en rollback.json. Para revertir, drenar la cola,
detener servicio, restaurar esos archivos/enlace y volver a iniciarlo.

## Alcance actual

`med u/r/f/v/d` cubre ingesta; `med rank` y `med basket` llaman analytics.
`med enrich` incorpora detalles de las ofertas ya elegidas y `med show` llama UX.
`med status` presenta estados de conversación. Show admite ranking, no basket.
El agente presenta opciones reportadas; no afirma mínimos globales al separar sales.

Se verificaron componentes con 190 ofertas reales y después una ejecución interna
de runAgent con la misma configuración: usó ingesta, rank, enrich y show y generó
una respuesta en 54,809 s. No se enviaron mensajes de prueba a Telegram. Ver
`docs/teams/flujo-integrado-verificacion.md` para cifras y límites del ensayo.
