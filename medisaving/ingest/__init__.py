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
    from .commands import resolve, fetch, detail, district
    command = commands.add_parser("u", help="Resolve district ubigeo (Lima province by default)")
    command.add_argument("query")
    command.add_argument("--province", default="1501")
    command.set_defaults(run=district)
    command = commands.add_parser("r", aliases=["resolve"], help="Resolve product IDs")
    command.add_argument("query")
    command.add_argument("strength", nargs="?")
    command.add_argument("--sl", action="store_true", help="Require SL in candidate name; verify actual offer form")
    command.add_argument("--fresh", action="store_true")
    command.set_defaults(run=resolve)
    command = commands.add_parser("f", aliases=["fetch"], help="Fetch district offers; return only ID and count")
    command.add_argument("ubigeo")
    command.add_argument("products", nargs="+")
    command.add_argument("--pages", type=int, default=3)
    command.add_argument("--fresh", action="store_true")
    command.add_argument("--stats", action="store_true")
    command.set_defaults(run=fetch)
    command = commands.add_parser("d", aliases=["detail"], help="Fetch one offer's official detail")
    command.add_argument("dataset_id")
    command.add_argument("offer_id")
    command.add_argument("--fresh", action="store_true")
    command.set_defaults(run=detail)


def import_offers(args, store):
    from .normalize import canonical_import
    data = validate_dataset(canonical_import(validate_dataset(json.loads(Path(args.path).read_text()))))
    return {"dataset_id": store.put(data), "count": len(data["offers"]),
            "source": data["source"]}
