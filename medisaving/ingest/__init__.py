"""Owned by ingestion team. Add commands here without editing the dispatcher."""
import json
from pathlib import Path
from ..core import validate_dataset


def register(areas):
    parser = areas.add_parser("ingest", help="Import normalized source data")
    commands = parser.add_subparsers(required=True)
    command = commands.add_parser("import", help="Import a normalized offers JSON file")
    command.add_argument("path")
    command.set_defaults(run=import_offers)


def import_offers(args, store):
    data = validate_dataset(json.loads(Path(args.path).read_text()))
    return {"dataset_id": store.put(data), "count": len(data["offers"]),
            "source": data["source"]}
