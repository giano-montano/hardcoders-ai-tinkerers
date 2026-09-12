# Verificación real: ingesta + analytics + UX

Fecha: 2026-09-12. Integración de main d2af1af con team/ingesta y adaptador runtime.
Bot: @MedSavings_bot. No se usaron 61k filas inventadas ni se repitió el caso viejo.

## Orden de comprobación

1. Suite combinada de los equipos: 41 tests pasaron antes del ensayo.
2. Smoke sin LLM en laptop, usando el mismo constructor bwrap de runAgent:
   resolución de distrito y tres productos, 190 ofertas reales de DIGEMID,
   lectura de detalle y caché. Código readonly y workspace privado verificados.
3. Analytics: el mínimo seleccionado para cada grupo se comprobó contra los
   precios de las ofertas descargadas. Concentración exacta y sublingual comprobadas.
4. Enriquecimiento: se unió presentación/fabricante del detalle oficial al resultado
   seleccionado; precios unitario y caja permanecieron idénticos al ranking.
5. UX: render real preservó farmacia, dirección y precios, con texto plano dentro
   del límite de Telegram. También respondió el comando de estado de distrito faltante.
6. Solo después se ejecutó runAgent en almacenamiento de prueba separado, con los
   mismos tres medicamentos en texto y Lince. 15 comandos, todos con exit 0; usó
   med u/r/f, tres rank, tres enrich y tres show, además de leer las skills.
7. Dos tests adicionales del adaptador verifican el join sin alterar precios,
   filtro exacto, render y fallo de detalle explícito. Suite final: 43 tests.

La prueba del agente no llama al receptor ni al envío de Telegram. Ejecuta la parte
interna del flujo que utiliza el servicio real. Cero envíos a usuarios de prueba.
La versión integrada se activó después con respaldo y cola sin trabajos pendientes.

## Consumo real del agente, no estimación de texto

| Métrica | Antes, navegador | Después, CLI completo | Reducción observada |
| --- | ---: | ---: | ---: |
| Entrada acumulada | 2.940.806 | 130.345 | 95,57% |
| Entrada en caché (incluida arriba) | 2.864.512 | 119.680 | — |
| Entrada sin caché | 76.294 | 10.665 | 86,02% |
| Salida | 5.804 | 1.630 | 71,92% |
| Entrada + salida | 2.946.610 | 131.975 | 95,52% |
| Duración task_started → task_complete | 343,627 s | 51,920 s | 84,89% |

El wrapper runAgent nuevo tardó 54,809 s incluyendo preparación/arranque y lectura
de respuesta. El turno nuevo fue 20:24:38.541–20:25:30.461 UTC. Produjo 1.045
caracteres, sin PDF. Los contadores vienen de turn.completed de Codex; los del
antes, del delta de contadores del rollout histórico ya conservado.

Artefacto agregado y hashes: `tests/integration/e2e-actual-result.json`.
Eventos y respuesta del ensayo quedan privados bajo data/local/full-flow-audit y
en test-runs/full-flow-20260912 de la laptop; no se commitearon los logs completos.

**Límites:** un ensayo por configuración, no un experimento controlado. Antes:
foto y conversación reanudada; después: mismos medicamentos en texto y sesión
nueva. Mismo modelo gpt-5.6-sol, razonamiento medium y laptop, pero distinto
contexto y recorrido. No atribuir todo el ahorro exclusivamente a analytics, ni
convertir tokens cacheados en dinero a tarifa de entrada normal. No se midieron
recepción/envío Telegram, carga concurrente ni una canasta con cantidades.

El 98,78% anterior medía solamente texto devuelto por herramientas con un
tokenizador de referencia. Esta tabla mide consumo real completo del agente y
debe ser la referencia para describir este nuevo ensayo en el pitch.

## Hallazgos y límites funcionales

- Faltaba filtro exacto de forma/concentración en rank: se añadieron --form y
  --strength. El contrato de claves no se cambia y no se normaliza dentro de analytics.
- UX recibía presentación ausente: med enrich consulta solo detalles elegidos y
  genera otro ranking enriquecido, conservando el original y todos sus precios.
- El wrapper anterior solo exponía ingesta: ahora enruta rank/basket/show/status
  y enrich al módulo correspondiente; las dos skills están disponibles en el sandbox.
- Escitalopram y escitalopram oxalato siguen separados deliberadamente. El ensayo
  eligió ESTAZYL, S/ 165 caja / S/ 5,50 unidad para la clave literal escitalopram;
  el histórico había mostrado otra oferta de S/ 104,30 caja. No es evidencia de
  ahorro en la compra ni de mínimo clínicamente equivalente global. Se ajustó
  después del ensayo el prompt para decir opciones reportadas y explicar el alcance.
  Resolver equivalencias verificadas de sales queda como trabajo de dominio pendiente.
- Basket tiene sus tests del equipo, pero no se invocó en este caso: no había
  cantidades explícitas. UX show admite Ranking, no Basket. No afirmar que el
  flujo de canasta tiene render E2E comprobado. La propagación/tratamiento de
  identity_status en basket todavía necesita revisión del equipo analytics.
- Analytics devuelve source completo en cada invocación: tres rank repiten esa
  metadata. Es una oportunidad de reducir salida y llamadas sin alterar resultados.
- La respuesta se genera en español sobre etiquetas del renderer inglés, conforme
  al bot existente. Localización determinista de UX evitaría esa transformación
  por el modelo; no se ha medido su beneficio.

No se generaron datos de precio inventados para el ensayo. Las pruebas unitarias
preexistentes y del adaptador usan fixtures, como pruebas de código; no se usaron
para afirmar el rendimiento sobre 190 ofertas reales.
