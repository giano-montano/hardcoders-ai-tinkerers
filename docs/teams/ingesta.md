# Equipo ingesta — mismo CLI

Rama: `team/ingesta`. Propiedad: `medisaving/ingest/`, `tests/ingest/`,
este documento y futura skill `skills/ingesta/`. No editar analytics, UX o bot.

## Punto de partida

`python -m medisaving ingest import examples/offers.synthetic.json` valida y guarda
el contrato Offers v1. Devuelve dataset_id y conteo, no miles de filas.
Leer `docs/cli-contract.md` y revisar `digemid_dump.py` / `HAPPY_PATH.md` como
referencias del cliente existente. No modificar el descargador compartido sin coordinar.

## Trabajo prioritario

1. Agregar `ingest resolve` para buscar catálogo local y devolver candidatos compactos.
   Resolver principio activo, concentración y forma; si son ambiguos, devolverlos
   explícitamente para que el agente pregunte. No convertir SL a tableta oral.
2. Agregar `ingest fetch` por producto y ubigeo usando acceso oficial permitido:
   timeout, paginación acotada, reintentos con backoff y límite de concurrencia.
   No descargar todo el país en una consulta interactiva.
3. Normalizar respuestas a Offers v1. Guardar raw separado; mapear codEstab a sucursal;
   verificar precio1/2, fracciones, presentación y laboratorio contra la fuente.
   Usar Decimal para convertir a céntimos, no floats. No inferir campos desconocidos.
4. Caché por consulta normalizada con TTL y fetched_at, cobertura explícita y
   resultados parciales ante páginas fallidas. Reutilizar consultas idénticas.
5. Skill breve: comandos, resolución ambigua, errores, caché y ejemplos de IDs.

## Listo cuando

Datos de fixtures oficiales anonimizados recorren import → rank → telegram sin
modificar otros módulos. Tests cubren páginas repetidas, parciales, vacías, timeout,
dinero ambiguo y forma/dosis. Medir consulta fría y caliente, requests y bytes de
stdout. Red real solo en smoke opcional, nunca requerida por CI.

```bash
python -m unittest discover -s tests/ingest -v
python -m unittest discover -v
```

Crear handoff propio. Si faltan campos en v1, proponer primero el cambio compartido.
