# UX interactiva integrada en el bot headless

Se integró origin/main 0109c9a en team/ingesta, conservando la resolución de identidad de ingesta. Además del renderer, se implementó el adaptador de entrega en prototypes/codex-telegram/src/ux.js y bot.js; no se modificó bot.py.

El agente devuelve presentation_id en response.presentations. El adaptador carga los artefactos del chat, entrega tarjetas con teclados y persiste la relación chat/mensaje/presentación/acciones. Las actualizaciones callback_query entran a la misma cola persistente y se deduplican por update_id. Detalles, teléfono reportado, expansión del ranking ya guardado y nueva conversación se resuelven sin LLM. El mapa abre una búsqueda por dirección de farmacia; no solicita ubicación. La acción teléfono muestra el número reportado, no inicia una llamada automáticamente.

La expansión solo existe cuando el ranking contiene más opciones de las visibles: no vuelve a buscar ni promete todas las ofertas de DIGEMID. Las tarjetas mantienen inglés del renderer de UX; el agente puede introducirlas en español. No se generan prescription_checks inferidos para activar alertas. Los mensajes antiguos sin tarjetas siguen siendo compatibles.

Se corrigió el renderer para conservar los teclados al dividir mensajes largos. Archivos de presentación y ranking con rutas fuera del chat se rechazan; callbacks se validan contra el usuario privado y el mensaje que recibió el teclado. Referencia del protocolo: https://core.telegram.org/bots/api#callbackquery y https://core.telegram.org/bots/api#inlinekeyboardbutton.

Verificación: 51 pruebas Python, 3 pruebas Node. Incluyen entrega del bot con transporte simulado, callback duplicado procesado una vez, autorización, rutas y teclados. Sandbox real en laptop con 190 ofertas: ingesta, ranking, detalle y UX pasan, cero llamadas LLM y cero envíos Telegram de prueba. No se hizo una nueva medición de tokens ni una prueba manual de pulsación desde Telegram.

Desplegado en releases/ux-interactions-20260912. Servicio medisaving.service activo, arranque confirmado como MedSavings_bot. Antes de activar: 10 trabajos terminados, ninguno pendiente. Backup en releases/pre-ux-interactions-20260912 incluye código, schema, instrucciones y enlace anterior del CLI; credenciales intactas.

Límite de entrega: se guarda progreso por tarjeta después de recibir la respuesta Telegram. Un corte entre aceptación remota y guardado local puede duplicar esa tarjeta al recuperar el proceso; no se afirma entrega exactly-once. Los callbacks duplicados por update_id sí se deduplican en la cola persistida.
