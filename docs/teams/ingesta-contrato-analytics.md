# Contrato propuesto de ingesta para analytics

Fecha: 2026-09-12. Base de implementación: `team/ingesta`, commit `3edf3b5`.
Responde a `docs/analytics-dependencias-ingesta.md` de `main` (`069ec85`).

**Estado: perfil implementado en ingesta, pendiente de acuerdo con analytics.**
No sustituye todavía `docs/cli-contract.md` ni declara aceptación por el otro equipo.
Los equipos pueden construir contra los ejemplos de este documento. Las diferencias
se resuelven aquí antes de modificar el contrato compartido o fusionar ramas.

## 1. Interfaz que se mantiene

```text
python -m medisaving --data-dir DIR ingest f UBIGEO PRODUCT_ID...
→ {"ok":true,"schema_version":1,"data":{"dataset_id":"…","n":190,"complete":true}}

python -m medisaving --data-dir DIR analytics rank DATASET_ID
```

El ejemplo de respuesta es ilustrativo: `warnings` aparece cuando corresponde.
Ambos procesos usan el mismo DIR, elegido por el servicio y aislado por chat.
Un fetch combina hasta diez productos en un distrito en **un dataset**.
No requiere que analytics reciba arrays por argumentos, use HTTP ni lea caché cruda.
Combinar distritos/datasets es una capacidad posterior, no un requisito del caso inicial.

Se conserva Offers `schema_version: 1`, precios y campos requeridos actuales.
Proponemos identificar el perfil de normalización con
`source.normalization: "text-v1"`. No se debe asumir ese perfil si el campo falta:
los artefactos históricos siguen siendo legibles, pero necesitan reimportación
para mezclarlos con datos nuevos bajo las mismas reglas de identidad.

## 2. Identidad y normalización a cargo de ingesta

Estas reglas deben aplicarse **tanto a fetch como a import**. Analytics puede
comparar los campos canónicos por igualdad exacta; no implementa su propio limpiador.

| Campo | Regla propuesta | Ejemplo |
| --- | --- | --- |
| `medicine_key` | Sustancia de fuente con Unicode NFC, casefold, trim y espacios internos colapsados. Conservar sales, acentos, puntuación y componentes. | ` ESCITALOPRAM  OXALATO ` → `escitalopram oxalato` |
| `strength` | Eliminar espacios, minúsculas, coma decimal → punto, números decimales sin ceros redundantes. Sin convertir unidades. | `020,00 MG` → `20mg`; `0,250 mg` → `0.25mg` |
| `form` | Unicode NFC, casefold, trim y espacios colapsados. No traducir ni fusionar sinónimos. | `Tableta Sublingual` → `tableta sublingual` |
| `medicine` | Nombre visible del producto, conservado con trim. No usar como clave de agrupamiento. | `ZATRIX SL` |
| `pharmacy_id` | Código de sucursal como string, conservando ceros iniciales. | `0099242` |
| `offer_id` | Identidad de sucursal + producto de fuente. Única dentro del dataset. | `0099242:45457` |

No convertir `1000mcg` en `1mg`, ni `20mg/1mL` en `20mg/mL` en este perfil.
No sustituir `tableta de desintegración oral` por `tableta sublingual`.
No colapsar `escitalopram oxalato` y `escitalopram`: decidir equivalencias de
sustancia/sales requiere una tabla verificada y otro acuerdo, no un cambio de texto.
Estas decisiones pueden separar ofertas potencialmente comparables; se prefiere
esa separación explícita a afirmar equivalencia sin evidencia.

**Sustancia ausente:** usar `medicine_key: "digemid:GRUPO"` y
`identity_status: "source_group_only"`. Si la sustancia existe:
`identity_status: "substance_reported"`. No unir automáticamente la clave de
respaldo con una sustancia conocida ni usarla para recomendar sustituciones.
El ranking puede mantener ese grupo separado; una canasta que exija una sustancia
conocida debe tratarlo como identidad pendiente, no como coincidencia confirmada.
En import, una medicine_key existente se normaliza como texto; las claves
`digemid:*` mantienen la condición de respaldo. No se inventa una sustancia.

Conservar los textos originales disponibles en `source_values` opcional de la
oferta: `substance`, `strength`, `form`. Esto permite auditar la normalización.
La ausencia de ese objeto en un import antiguo no impide importarlo.

## 3. Dinero, sucursal y campos opcionales

Ya implementado: moneda PEN; precios unitario/caja en céntimos enteros positivos
o null; fracciones enteras positivas o null. Decimal sin redondeo silencioso.
No calcular precio unitario dividiendo caja ni inferir fracciones desconocidas.
Datos numéricos ambiguos se rechazan y se contabilizan; no se convierten en cero.

Proponemos registrar como extensiones opcionales de Offers v1:

| Campo de oferta | Tipo | Uso |
| --- | --- | --- |
| `source_product_id` | string | Consulta de detalle de producto |
| `source_group` | string | Grupo del catálogo oficial |
| `source_form_group` | string | Familia de fuente, no forma clínica exacta |
| `ubigeo` | string de 6 dígitos | Distrito consultado |
| `identity_status` | enum descrito arriba | Distinguir sustancia reportada de respaldo |
| `source_values` | objeto de textos/null | Evidencia original para normalización |

Los seis campos ya se producen en fetch; import conserva los opcionales disponibles
y añade identity_status y source_values mediante el mismo normalizador.
Analytics conserva campos desconocidos, pero no necesita ninguno de estos para
su ranking básico. Los imports antiguos no requieren códigos de DIGEMID para ser
válidos. Sin identificadores oficiales suficientes no se puede ejecutar `ingest d`.

## 4. Cobertura y advertencias que viajarán dentro del dataset

`source.complete` significa cobertura de grupos y ubicación consultados, después
de validación. Nunca significa stock, receta completa o equivalencia clínica.
`fetched_at` conserva la fecha de adquisición más antigua entre las respuestas
utilizadas, incluso si se sirvieron desde caché. No rejuvenecer datos cacheados.

Además de `name`, `fetched_at`, `scope` y `complete`, proponemos:

- `normalization`: `"text-v1"` para datos procesados con este perfil.
- `warnings`: array de códigos; vacío si no hay advertencias. **Persistido en source**.
- `coverage`: array por producto consultado; contiene `product` con `group`, `ff`,
  `strength`, además de `rows`, `total`, `complete`. `total` puede ser null.
  `rows` cuenta filas recibidas, incluyendo solapamientos de páginas; no confundirlo
  con ofertas únicas aceptadas. Es cobertura de descarga por producto.
- `rejected_rows`: entero con filas rechazadas al normalizar el dataset.
- `duplicate_rows`: entero con repeticiones de identidad detectadas al normalizar.

Si hay rechazos o duplicados contradictorios, source.complete=false aunque las
páginas estén completas. `source.coverage[*].complete` puede seguir true porque
describe descarga; los contadores y warnings explican la pérdida posterior.

| Código de warning | Significado |
| --- | --- |
| `partial` | No se pudo demostrar cobertura completa de alguna consulta |
| `source_error` | Falló una respuesta de fuente |
| `repeated_page` | La fuente repitió una página y se detuvo la descarga |
| `source_changed_during_pagination` | Cambió el total reportado durante la consulta |
| `rejected_rows` | Filas no utilizables por identidad, ubicación, concentración o dinero |
| `conflicting_duplicate` | Misma identidad con datos diferentes; no resolver silenciosamente |
| `verify_offer_forms` | Un grupo/concentración incluye formas distintas; no inferir equivalencia |
| `diagnostics_unavailable` | Import de datos anteriores sin advertencias de origen; no asumir ausencia de problemas |

La ausencia de warnings en un dataset antiguo significa «sin diagnóstico
disponible», no «sin problemas». Analytics debe reenviar source intacto y puede
resumir estos códigos sin leer artefactos de estadísticas ni logs de ingesta.
Al reimportar esos datos se hace explícito `diagnostics_unavailable`. Los contadores
ausentes se inicializan a cero para la operación actual de importación; no prueban
que la descarga histórica haya tenido cero rechazos. Se preservan contadores previos
si existen y source.complete=false ante rechazos previos o duplicados contradictorios.

## 5. Ejemplo mínimo de identidad para fixtures del equipo analytics

Agregar estos valores a ofertas sintéticas con el resto de campos Offers v1:

```json
{
  "medicine_key": "clonazepam",
  "identity_status": "substance_reported",
  "medicine": "DEMO SL",
  "strength": "0.25mg",
  "form": "tableta sublingual",
  "source_values": {
    "substance": "CLONAZEPAM",
    "strength": "0,25 mg",
    "form": "Tableta Sublingual"
  }
}
```

Otra oferta con `form: "tableta de desintegración oral"` debe formar otro grupo.
Otra con `medicine_key: "digemid:1058"` e identidad source_group_only tampoco se
fusiona automáticamente con la anterior, aunque coincidan concentración y forma.

## 6. Trabajo paralelo y condición de integración

**Ingesta se encarga de:** aplicar el mismo perfil en import/fetch, preservar
evidencia original, persistir advertencias/cobertura, y probar la salida del fetch
real como pipeline de código con respuestas HTTP grabadas y anonimizadas en tests.
Estas tareas ya están implementadas en la rama de ingesta. Las pruebas invocan rank
sin modificar su implementación y no dependen de llamadas reales a DIGEMID en CI.
También están listos HTTP, caché, precios,
identificadores, descarga de varios medicamentos en un distrito y detección de formas.

**Analytics puede avanzar ya en sus archivos:** filtros/ranking sobre estos campos,
canasta con cantidades explícitas y faltantes, desembolso por cajas completas,
benchmark de 61k filas sintéticas y skill de uso. No necesita esperar otra descarga.
No modifica normalizadores ni reimplementa consultas a la fuente.

**Integración compartida:** confirmar este perfil y las extensiones opcionales,
actualizar `docs/cli-contract.md` y el fixture común en un cambio coordinado,
ejecutar pruebas de ambos equipos y entonces integrar ingesta a main. No migrar
artefactos históricos en silencio. Esta propuesta no autoriza editar archivos del
otro equipo ni afirma que analytics ya haya aceptado las decisiones.

Pruebas de esta entrega: `tests/ingest/test_contract.py`, fixture documentado en
`tests/ingest/fixtures/README.md`. Cubren fetch → rank directo, import + fetch con
formatos equivalentes, identidad desconocida, separación de sales, conservación
de datos originales, idempotencia y propagación de diagnósticos a Ranking v1.
