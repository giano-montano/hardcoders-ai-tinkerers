import argparse
import json
import sys

from . import ingest, analytics, ux
from .core import Store


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m medisaving")
    parser.add_argument("--data-dir", default="data/local/medisaving")
    areas = parser.add_subparsers(dest="area", required=True)
    for module in (ingest, analytics, ux):
        module.register(areas)
    args = parser.parse_args(argv)
    try:
        data = args.run(args, Store(args.data_dir))
        result = {"ok": True, "schema_version": 1, "data": data}
        code = 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result = {"ok": False, "schema_version": 1,
                  "error": {"code": "INVALID_INPUT_OR_STORAGE", "message": str(exc)}}
        code = 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
