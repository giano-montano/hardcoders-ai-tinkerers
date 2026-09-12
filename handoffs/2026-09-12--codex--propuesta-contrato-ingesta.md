# Contrato propuesto para desbloquear trabajo paralelo

Se publica `docs/teams/ingesta-contrato-analytics.md` como respuesta técnica al
análisis de dependencias de analytics. Define identidad canónica para import/fetch,
tratamiento conservador de sustancias desconocidas y sales, extensiones opcionales,
cobertura, advertencias persistidas y responsabilidades de cada equipo.

Es una propuesta explícita, no un acuerdo aceptado ni funcionalidad ya implementada.
No se modificaron core, contrato compartido, fixtures comunes ni código de analytics.
Analytics puede preparar fixtures y desarrollar contra este perfil mientras ingesta
implementa sus pendientes. Confirmar las reglas antes de fusionar el cambio compartido.

Validación de esta entrega documental: revisión contra código y contrato vigentes,
ejemplos y `git diff --check`. No requiere volver a consultar la API ni ejecutar LLM.
