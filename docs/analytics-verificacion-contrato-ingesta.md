# Verificación del contrato propuesto por ingesta

Responde a `docs/teams/ingesta-contrato-analytics.md`
(`origin/team/ingesta`, commit `f6a96fd`, propuesta del 2026-09-12).
Método: leer la propuesta completa y cruzarla contra el código real de la
misma rama (`medisaving/ingest/normalize.py`, `commands.py`, commit `3edf3b5`)
y contra `medisaving/core.py` en `main`, no solo contra lo que el documento
afirma que hace.

## Compatible con el código actual sin cambios

- `core.validate_dataset` no rechaza campos desconocidos, así que
  `identity_status`, `source_values`, `source.normalization`, `source.warnings`,
  `source.coverage`, `rejected_rows` y `duplicate_rows` pasan la validación de
  `main` tal cual, sin tocar `core.py`.
- El diseño ya aprobado para `analytics rank`/`basket` (comparar
  `medicine_key`/`strength`/`form` por igualdad exacta de string, sin
  normalizador propio) sigue siendo válido **si** ingesta aplica el perfil de
  texto que promete. Ver discrepancia abajo: hoy no lo aplica del todo.
- `identity_status: source_group_only` resuelve el riesgo de
  `docs/analytics-dependencias-ingesta.md` sobre claves `digemid:*` sin
  sustancia: con este campo, analytics puede distinguir "coincidencia
  confirmada" de "identidad pendiente" en vez de tratarlas igual.

## Discrepancia encontrada: la normalización de `strength` no está implementada como se documenta

`normalize.strength()` en `origin/team/ingesta` (commit `3edf3b5`) es:

```python
def strength(value):
    return re.sub(r"\s+", "", str(value)).lower().replace(",", ".")
```

Solo quita espacios, pasa a minúsculas y cambia coma por punto — no parsea el
número, así que no colapsa ceros. Los propios ejemplos de la propuesta no
sobreviven al código real:

| Entrada | Propuesta promete | Código real produce |
| --- | --- | --- |
| `"020,00 MG"` | `"20mg"` | `"020.00mg"` |
| `"0,250 mg"` | `"0.25mg"` | `"0.250mg"` |

`tests/ingest/test_source.py` solo ejercita `"20 mg"` (ya limpio); no hay caso
con ceros a la izquierda o decimales redundantes, así que el gap no se
detectó en la propia suite de ingesta.

**Impacto en analytics:** si dos ofertas del mismo medicamento llegan como
`"20mg"` y `"020.00mg"` (mismo valor, texto distinto), `rank`/`basket` las
trata como grupos *diferentes* por comparación exacta — exactamente el riesgo
de fragmentación que señalé en `docs/analytics-dependencias-ingesta.md`, y que
este contrato dice resolver pero el código todavía no resuelve.

## Puntos que acepto para avanzar en paralelo

- Estructura general de identidad (`medicine_key`/`strength`/`form` por
  igualdad exacta, sin normalizador propio en analytics).
- `identity_status` (`substance_reported` / `source_group_only`) y su regla:
  una canasta que exige sustancia conocida debe tratar `source_group_only`
  como identidad pendiente, no como coincidencia confirmada.
- `source.coverage`/`warnings`/`rejected_rows`/`duplicate_rows` como campos
  que analytics reenvía intactos (ya es el comportamiento actual de `rank`,
  que copia `dataset["source"]` completo) sin necesidad de interpretarlos.
- Los campos ya implementados en fetch (`source_product_id`, `source_group`,
  `source_form_group`, `ubigeo`) — analytics los ignora, no los necesita.

## Qué falta antes de aceptar el contrato como acordado

1. **Arreglar `normalize.strength()`** para que canonice el número (parsear
   como `Decimal`, quitar ceros a la izquierda y ceros decimales redundantes)
   antes de fusionar `team/ingesta` a `main`, y agregar un test con entrada
   tipo `"020,00 MG"` — hoy la propuesta describe un comportamiento que el
   código no tiene.
2. `source_values` y `identity_status` figuran como "compromiso pendiente" en
   la propia propuesta (sección 3): no están implementados todavía en
   `commands.py`/`normalize.py` de la rama. Analytics puede diseñar `basket`
   asumiendo que existirán, pero no puede probarlos contra datos reales hasta
   que ingesta los implemente.
3. Confirmar si `medicine_key` realmente pasa por NFC+casefold+trim como dice
   la tabla de la sección 2 — `normalize.py` actual no toca `medicine_key`
   (`normalize.offer()` solo hace `.strip()` sobre todos los campos string,
   sin casefold ni NFC). Mismo tipo de discrepancia que con `strength`.

## Cómo esto ajusta el plan de analytics ya aprobado

No cambia el diseño de `basket` (archivo, formato de entrada JSON, tres
cifras de costo separadas, `single_branch`/`multi_branch`/`missing`) descrito
en el plan aprobado. Sí agrega una responsabilidad puntual:

- Cuando un ítem de la canasta matchee ofertas con
  `identity_status == "source_group_only"`, marcarlas explícitamente en el
  resultado (no como coincidencia confirmada), siguiendo la regla de la
  sección 2 de la propuesta. Si el campo no está presente (fixtures/imports
  antiguos), tratar la oferta como antes — sin ese matiz.
- La skill (ítem 5 del roadmap) debe explicar que el perfil de normalización
  de texto de ingesta **todavía no está completo** (ver discrepancia arriba),
  así que dos strings visualmente distintos para el mismo valor numérico
  pueden no agruparse — no es un bug de analytics si eso ocurre con datos
  reales antes de que ingesta corrija `normalize.strength()`.

## Recomendación

Aceptar la propuesta como base de trabajo en paralelo (no bloquea el plan de
analytics), pero responder a ingesta señalando el punto 1 (normalización de
`strength` no implementada como se documenta) como corrección necesaria antes
de fusionar `team/ingesta` a `main` o de dar por cerrado el contrato.
