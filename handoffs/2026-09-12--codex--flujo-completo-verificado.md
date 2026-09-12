# Ingesta + analytics + UX integrados y probados

Se incorporó main d2af1af a team/ingesta y se desplegó el conjunto en
@MedSavings_bot, release full-flow-20260912. Receptor Telegram y token sin cambios.
Respaldo del runtime anterior en releases/pre-full-flow-20260912.

Antes de ejecutar el agente: suite combinada, ingesta real (190 ofertas), mínimo
del ranking, selección sublingual, detalle sin cambios en precios y UX con precio,
dirección y límites de Telegram verificados. Después: runAgent real en directorio
aislado, sin envíos Telegram. Suite final: 43 pruebas pasaron.

Cambios mínimos para unir las piezas: flags --form/--strength en rank; wrapper
med rank/basket/show/status/enrich; join de detalle en nuevo ranking; prompt y skills
actualizados. No se reescribió el algoritmo de ranking/canasta ni el renderer de UX.

Consumo real: entrada 2.940.806 → 130.345; entrada sin caché 76.294 → 10.665.
Turno 343,627 → 51,920 s; wrapper nuevo 54,809 s. Ver
docs/teams/flujo-integrado-verificacion.md y tests/integration/e2e-actual-result.json.
No confundir esta medición con el 98,78% anterior de texto de herramientas.

Pendientes explícitos: equivalencias verificadas de sales, localización determinista
de UX, render de canasta y tratamiento de identity_status en basket. La consulta
ensayada no tenía cantidades, por eso no se probó canasta en este recorrido.
Prompt ajustado tras observar el resultado para no prometer mínimos globales.
