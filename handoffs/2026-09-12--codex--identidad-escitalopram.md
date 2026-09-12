# Identidad de búsqueda de escitalopram

Implementado en ingesta, sin modificar algoritmos de analytics o UX. Regla acotada OPM 1515:3:20mg; preserva concentración, forma y evidencia original. Contrato y fuentes: docs/teams/ingesta-identidad.md.

47 pruebas unitarias/integración pasan. Prueba del sandbox real en laptop: 190 ofertas, ranking mínimo verificado por forma, detalle y UX correctos para los tres medicamentos, caché caliente con cero consultas HTTP; aislamiento y CLI de solo lectura comprobados. Cero llamadas LLM y cero envíos Telegram en esta validación.

Captura real fija de escitalopram: 23 a 122 ofertas elegibles. Tableta recubierta: caja 30 de S/165 a S/105; comprimido recubierto separado S/104.30. Archivo agregado tests/ingest/identity-actual-result.json, con hash de captura. No es una nueva medición de ahorro de tokens ni una garantía de stock/intercambiabilidad.

Activado en laptop: releases/identity-20260912, servicio medisaving.service; ningún trabajo pendiente durante la activación (10 terminados). Copia de reversión: releases/pre-identity-20260912. Se mantuvieron credenciales y conversaciones. Nuevas consultas usan f para obtener artefactos con opm-identity-v1; los antiguos no se reescriben.

Siguiente ampliación requiere evidencia específica por sustancia, concentración y forma; no agregar eliminación genérica de sales. No se certificaron aún otras concentraciones de escitalopram ni otras sales.
