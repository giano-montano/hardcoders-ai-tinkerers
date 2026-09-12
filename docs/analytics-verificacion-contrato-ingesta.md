# Verificación del contrato propuesto por ingesta

Responde a `docs/teams/ingesta-contrato-analytics.md`
(`origin/team/ingesta`, commit `f6a96fd`, propuesta del 2026-09-12).
Método: leer la propuesta completa y cruzarla contra el código real de la
misma rama (`medisaving/ingest/normalize.py`, `commands.py`, commit `3edf3b5`)
y contra `medisaving/core.py` en `main`, no solo contra lo que el documento
afirma que hace.

## Estado: discrepancia resuelta en `c0b29b5`

El commit `c0b29b5` ("Unify ingestion normalization and persist dataset
diagnostics", `origin/team/ingesta`) corrige los tres puntos señalados abajo.
Verificado corriendo el código real (no solo leyendo el diff), en un worktree
temporal sobre ese commit:

- `strength("020,00 MG")` → `"20mg"` y `strength("0,250 mg")` → `"0.25mg"`,
  igual que promete la propuesta (antes producía `"020.00mg"`/`"0.250mg"`).
- `medicine_key`/`form` ahora pasan por `normalize.text()`
  (NFC + casefold + colapso de espacios):
  `" ESCITALOPRAM  OXALATO "` → `"escitalopram oxalato"`.
- `canonical_import()`/`canonical_offer()` aplican el mismo perfil tanto a
  `ingest import` como a `ingest fetch`, con `identity_status`/`source_values`
  ya implementados (antes figuraban como "compromiso pendiente").
- Suite completa en ese commit: 29/29 tests OK, incluyendo un test nuevo
  (`test_fetch_directly_consumed_by_rank`) que ejercita `ingest fetch` →
  `analytics rank` de punta a punta.

El resto de este documento queda como registro de la discrepancia original y
cómo se verificó su corrección.

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

## Qué faltaba antes de aceptar el contrato como acordado (resuelto en `c0b29b5`)

1. ~~**Arreglar `normalize.strength()`**~~ Resuelto: ahora canoniza el número
   vía `Decimal`, con test `test_strength_canonical_decimal_without_unit_conversion`
   cubriendo `"020,00 MG"` y casos equivalentes.
2. ~~`source_values` y `identity_status` "compromiso pendiente"~~ Resuelto:
   `canonical_offer()` los implementa y `test_contract.py` los prueba.
3. ~~Confirmar NFC+casefold+trim en `medicine_key`~~ Resuelto:
   `normalize.text()` se aplica a `medicine_key` y `form` vía `canonical_offer`/
   `canonical_import`.

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

Con `c0b29b5` ya no hay bloqueos técnicos conocidos para tratar la propuesta
de `docs/teams/ingesta-contrato-analytics.md` como acordada. `analytics rank`/
`basket` (`medisaving/analytics/`) siguen sin normalizador propio, apoyados en
que ingesta aplica el perfil de texto de forma simétrica en `import`/`fetch`.
