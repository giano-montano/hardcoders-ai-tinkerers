# Handoff — UX CLI Telegram renderer

**Fecha:** 2026-09-12  
**Autor:** ux  
**Estado:** aplicado sobre los archivos incorporados; sin cambios a bot, receta, ingesta ni analytics.

## Entrega

`python -m medisaving ux telegram RESULT_ID` ahora renderiza resultados Ranking v1 como texto plano para Telegram. Por defecto muestra hasta dos opciones por medicamento y comunica cuántas opciones comparables quedaron disponibles; con `--expand` muestra todas las seleccionadas. Cada opción reporta medicamento, concentración, forma, sucursal, distrito, dirección, laboratorio, precios de unidad/caja, unidades por caja, presentación, teléfono y fecha; los datos ausentes aparecen como `not reported`.

La cobertura parcial siempre queda visible en el mensaje fuente. El renderer no recalcula precios, no consulta HTTP y no envía mensajes.

## Estados y recuperación

Se añadió `python -m medisaving ux status STATE` para plantillas explícitas: `unreadable_photo`, `missing_district`, `ambiguous_query`, `no_results`, `error` y `recover`. El CLI no inventa información faltante.

## Seguridad operativa

Los mensajes siguen con `parse_mode: null`, se fragmentan bajo el límite UTF-16 de Telegram y el artefacto incluye métricas de render y bytes de salida. La entrega real queda para un adaptador coordinado con el dueño de `bot.py`, con destino autorizado e idempotencia por `presentation_id`.

No se generó imagen/PDF: UX indica texto primero y solo crear esos artefactos cuando aporten o sean solicitados. Se añadió `skills/ux/SKILL.md` como guía breve para usar el CLI e interpretar sus límites.

## Verificación

```bash
python -m unittest discover -s tests/ux -v
python -m unittest discover -v
```

La suite de UX pasó (4 pruebas) y el smoke `python -m medisaving ux status
recover` creó un `presentation_id`. La suite completa sigue fallando en el
almacenamiento compartido: `medisaving/core.py` lee los JSON sin declarar
`encoding="utf-8"`, por lo que Windows intenta CP1252 y falla con los datos de
prueba Unicode. No se modificó ese módulo porque no pertenece a UX.
