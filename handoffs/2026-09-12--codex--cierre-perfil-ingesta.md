# Perfil text-v1 implementado en ingesta

Se completó la parte de ingesta del contrato propuesto, sin modificar core,
analytics, UX, dispatcher, fixtures comunes o bot. Pendiente confirmar el acuerdo
con analytics y actualizar el contrato compartido antes de integrar a main.

- Import y fetch aplican el mismo normalizador a medicine_key, strength y form.
- source_values conserva los valores originales; normalización idempotente.
- identity_status identifica claves de respaldo sin declarar sustancia conocida.
- No se fusionan sales, formas ni unidades; se preservan códigos de sucursal.
- source incluye perfil, advertencias y contadores; fechas de caché se conservan.
- Import anterior sin warnings recibe diagnostics_unavailable; no se asume descarga
  histórica libre de errores. Artefactos existentes no se migran automáticamente.

Evidencia: `tests/ingest/test_contract.py` prueba fetch → rank directamente y
fetch + import → rank con texto equivalente, además de propagación de cobertura,
rechazos e identidad desconocida. Fixture derivado de respuesta oficial con
establecimientos/contactos sintéticos; origen documentado junto al JSON.

Validación: 24 pruebas de ingesta, 29 en suite completa; skill validada.
Sin nueva sesión LLM, sin requests reales a DIGEMID, sin envíos a Telegram.
Se actualizó `docs/teams/ingesta-contrato-analytics.md` distinguiendo implementación
local de aceptación por el equipo consumidor.
