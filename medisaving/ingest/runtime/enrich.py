"""Join official details to already-selected offers, without changing their prices."""
import argparse
from copy import deepcopy
import json
import sys
from types import SimpleNamespace
from ...core import Store
from ..commands import detail


def enrich(result_id, store):
    ranked = deepcopy(store.get(result_id, "ranking"))
    offers = [row for group in ranked["groups"] for row in group["offers"]]
    if len(offers) > 20:
        raise ValueError("Enrichment limit is 20 selected offers; use rank --top 1")
    failed = 0
    for row in offers:
        try:
            info = detail(SimpleNamespace(dataset_id=ranked["dataset_id"], offer_id=row["offer_id"], fresh=False), store)
            row["presentation"] = info.get("presentacion") or row.get("presentation")
            row["laboratory"] = info.get("nombreFabricante") or info.get("laboratorio") or row.get("laboratory")
            row["detail_id"] = info["detail_id"]
        except (ValueError, KeyError, OSError, TypeError):
            failed += 1
    ranked["detail_enrichment"] = {"parent_result_id": result_id, "selected": len(offers), "failed": failed}
    if failed:
        ranked["source"].setdefault("warnings", []).append("detail_unavailable")
    return {"result_id": store.put(ranked), "selected": len(offers), "detail_failures": failed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result_id")
    parser.add_argument("--data-dir", default="/work/ingest")
    args = parser.parse_args()
    try:
        data = enrich(args.result_id, Store(args.data_dir))
        print(json.dumps({"ok": True, "schema_version": 1, "data": data}))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
