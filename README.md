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
--------------------------------------------------------------------------------------------------------------------------------------------------
 
Below is a quick preview of MedSavings Bot in action: processing medical prescriptions, querying DIGEMID pricing and pharmacy availability, and delivering real-time, location-based options.

<img width="932" height="971" alt="image" src="https://github.com/user-attachments/assets/43377379-6eda-4d48-a472-d022e5dd69fb" />

<img width="912" height="966" alt="image" src="https://github.com/user-attachments/assets/2e01759f-7529-4f1c-8246-31a1cdd8427a" />

<img width="907" height="970" alt="image" src="https://github.com/user-attachments/assets/d072ef17-6af2-49ff-84d4-9f89f41ce4e4" />

  <img width="976" height="952" alt="image" src="https://github.com/user-attachments/assets/2dc54ac1-001e-4eb4-80d6-d631079f4321" />

  <img width="1878" height="1197" alt="image" src="https://github.com/user-attachments/assets/61159cd6-5a78-4949-80b4-a8f58131b5f0" />




