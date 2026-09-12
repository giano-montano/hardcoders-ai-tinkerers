# Medisaving CLI

Un CLI, tres módulos independientes. Python 3.14, sin dependencias.
El bot existente (`bot.py` / `receta.py`) conserva su contrato y ejecución.

```bash
python -m medisaving --help
python -m medisaving ingest import examples/offers.synthetic.json
python -m medisaving analytics rank DATASET_ID --district 'San Isidro' --top 3
python -m medisaving ux telegram RESULT_ID
python -m unittest discover -v
```

Reemplazar los IDs con los que devuelve el comando anterior. Salida JSON compacta;
los registros completos quedan en `data/local/medisaving/`, ignorado por Git.
Para aislar chats o pruebas: `python -m medisaving --data-dir RUTA ...`.
El servicio debe elegir esa ruta, nunca aceptar una ruta enviada por Telegram.

**Funciona hoy:** importar ofertas normalizadas, ordenar precios comparables y
renderizar texto para Telegram. El ejemplo es sintético, no ofrece precios reales.
El CLI no consulta aún DIGEMID, no envía mensajes ni genera imágenes/PDF.
Esas son las extensiones asignadas a los equipos, no funcionalidades simuladas.

- [Ingesta](docs/teams/ingesta.md): consultas, normalización y caché.
- [Analytics](docs/teams/analytics.md): comparación, filtros y canastas.
- [UX](docs/teams/ux.md): conversación, Telegram y artefactos visuales.
- [Contrato compartido v1](docs/cli-contract.md).

Cada equipo trabaja en su rama y sus carpetas. El dispatcher carga `register()`
de cada módulo; agregar comandos dentro del módulo no requiere tocar el dispatcher.
Cambios a `medisaving/core.py`, el contrato o la integración del bot se coordinan
en un PR separado. No cambiar archivos de otro equipo para desbloquear el propio.

La mejora esperada es sacar descarga, filtrado y aritmética del contexto del modelo.
No hay una reducción de latencia medida todavía: los equipos deben registrar
tiempo de fuente, cómputo y render, bytes de salida y aciertos de caché.
