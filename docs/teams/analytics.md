# Equipo analytics — mismo CLI

Rama: `team/analytics`. Propiedad: `medisaving/analytics/`, `tests/analytics/`,
este documento y futura skill `skills/analytics/`. No editar ingesta, UX o bot.

## Punto de partida

`python -m medisaving analytics rank DATASET_ID --district 'San Isidro' --top 3`
ordena por unidad; `--basis pack` compara cajas de igual tamaño conocido.
Devuelve result_id y conteos. Leer `docs/cli-contract.md`.
La base ya separa concentración/forma y sucursales, y excluye precios desconocidos.

## Trabajo prioritario

1. Mejorar filtros y ranking sobre artefactos locales, sin red ni LLM. Conservar
   referencia de fuente y precio, y explicar exclusiones en resúmenes compactos.
2. Agregar canasta por cantidades explícitas. Comparar compra en una sucursal
   frente a varias; mostrar faltantes. No deducir cantidad de una dosis incompleta.
3. Separar costo unitario teórico, cajas enteras necesarias y desembolso real.
   Calcular ahorro solo con alternativas comparables y referencia identificada.
4. Medir memoria y tiempo con 61k filas sintéticas; escoger índices/SQLite si aporta.
   Top-k y agregados deben quedar acotados aunque el dataset crezca.
5. Skill breve para elegir comando, interpretar parciales y pedir cantidades faltantes.

## Listo cuando

Tests cubren mezclas de dosis/formas, cajas distintas, precios nulos, duplicados,
empates, cantidad insuficiente y canasta incompleta. Jamás declarar que una farmacia
tiene todas las medicinas por compartir nombre de cadena. Benchmark reproducible
antes/después; no prometer latencia sin medir. Mantener el contrato Ranking v1 para
UX; nuevos tipos de resultado se acuerdan primero.

```bash
python -m unittest discover -s tests/analytics -v
python -m unittest discover -v
```

Crear handoff propio. No modificar core/dispatcher para agregar subcomandos.
