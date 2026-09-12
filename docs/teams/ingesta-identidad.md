# Identidad de búsqueda OPM — opm-identity-v1

Problema: el filtro literal `--medicine escitalopram` excluía ofertas cuyo nombre de sustancia era ESCITALOPRAM OXALATO, aunque OPM las devuelve bajo el mismo candidato y concentración.

Regla `opm-1515-3-20mg-escitalopram-v1`: solo source_group=1515, source_form_group=3, concentración nominal reportada 20mg y forma tableta recubierta o comprimido recubierto. Los nombres exactos normalizados escitalopram y escitalopram oxalato reciben medicine_key=escitalopram. Las formas conservan grupos separados. No se modifican precios, fracciones, laboratorio ni nombre comercial.

Evidencia consultada el 2026-09-12:

- [OPM DIGEMID](https://opm-digemid.minsa.gob.pe/#/consulta-producto): respuesta real conservada localmente para grupo 1515:3:20mg, distrito 150116. 122 ofertas: 23 ESCITALOPRAM y 99 ESCITALOPRAM OXALATO, todas con concentración nominal 20 mg. Es evidencia del catálogo, no de intercambiabilidad entre marcas. La captura privada no se publica.
- [Ficha FDA Lexapro, sección 11, página 21](https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/021323s058lbl.pdf): describe la sustancia como escitalopram en sal oxalato y distingue masa de sal de dosis equivalente de base. Sirve de respaldo químico; no certifica cada producto peruano. Por ello esta regla normaliza identidad de búsqueda del catálogo OPM y no convierte concentraciones.

Exclusiones: 10mg aún no verificado en nuestro flujo, 25.5mg expresados como masa de sal, otras sales, combinaciones, soluciones, sublinguales, grupos distintos y sustancia ausente. No hay eliminación genérica de sufijos ni afirmación de sustitución clínica.

Contrato aditivo: source.normalization sigue siendo text-v1; source.identity_profile=opm-identity-v1 señala la nueva resolución. Cada fila coincidente conserva source_values y añade identity_rule. identity_status sigue indicando si la sustancia fue reportada o solo se conoce el grupo. Perfiles/reglas desconocidos se rechazan al importar.

Migración explícita: `f` normaliza la respuesta cruda incluso cuando viene de caché; `import` crea un artefacto nuevo y conserva evidencia. No se reescriben datasets ni rankings guardados. Analytics consume medicine_key como antes, sin cambios de algoritmos. Para una consulta nueva, ejecutar `f` y crear un ranking nuevo.

Verificación sobre la misma captura real: antes eran elegibles 23/122 ofertas; después 122/122. Tableta recubierta pasa de S/5.50 por unidad y S/165 por caja de 30 a S/3.50 y S/105. Además aparece el grupo separado comprimido recubierto: S/3.48 y S/104.30 por caja de 30. Precios reportados, no stock confirmado. Evidencia agregada en tests/ingest/identity-actual-result.json. No se midieron tokens nuevos para este cambio.
