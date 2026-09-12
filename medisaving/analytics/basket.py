"""Owned by analytics team. No HTTP or presentation dependencies.

Never infers a quantity, a pack size, or a price. Every figure is either
computed from explicit dataset fields or left null; nothing is guessed to
make a basket look complete.
"""
import json
from pathlib import Path


def register(commands):
    command = commands.add_parser("basket", help="Compare an explicit-quantity basket across pharmacies")
    command.add_argument("dataset_id")
    command.add_argument("items_path", help="JSON array of {medicine_key, strength, form, quantity}")
    command.add_argument("--district")
    command.add_argument("--basis", choices=("unit", "pack"), default="unit")
    command.set_defaults(run=basket)


def _parse_items(path):
    items = json.loads(Path(path).read_text())
    if not isinstance(items, list) or not items:
        raise ValueError("Items file must contain a non-empty array")
    parsed = []
    for entry in items:
        if not isinstance(entry, dict):
            raise ValueError("Each basket item must be an object")
        for field in ("medicine_key", "strength", "form"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(f"Basket item {field} is required")
        quantity = entry.get("quantity")
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("Basket item quantity must be a positive integer")
        parsed.append({"medicine_key": entry["medicine_key"], "strength": entry["strength"],
                       "form": entry["form"], "quantity": quantity})
    return parsed


def _match_key(medicine_key, strength, form):
    return (medicine_key.casefold().strip(), strength.casefold().strip(), form.casefold().strip())


def _price_candidate(row, quantity, basis):
    unit_price, pack_price, pack_units = (row.get("unit_price_cents"), row.get("pack_price_cents"),
                                          row.get("pack_units"))
    theoretical_unit_cost_cents = unit_price * quantity if unit_price is not None else None
    packs_needed = rounded_up = pack_total_cents = None
    if pack_units is not None:
        packs_needed = -(-quantity // pack_units)  # ceil; never buy a partial box
        rounded_up = quantity % pack_units != 0
        if pack_price is not None:
            pack_total_cents = packs_needed * pack_price
    actual = theoretical_unit_cost_cents if basis == "unit" else pack_total_cents
    return {"pharmacy_id": row["pharmacy_id"], "pharmacy": row["pharmacy"], "offer_id": row["offer_id"],
            "unit_price_cents": unit_price, "pack_price_cents": pack_price, "pack_units": pack_units,
            "theoretical_unit_cost_cents": theoretical_unit_cost_cents, "packs_needed": packs_needed,
            "rounded_up": rounded_up, "pack_total_cents": pack_total_cents,
            "actual_disbursement_cents": actual}


def _cheaper(candidate, current):
    if candidate["actual_disbursement_cents"] is None:
        return False
    if current["actual_disbursement_cents"] is None:
        return True
    if candidate["actual_disbursement_cents"] != current["actual_disbursement_cents"]:
        return candidate["actual_disbursement_cents"] < current["actual_disbursement_cents"]
    return candidate["offer_id"] < current["offer_id"]


def _resolve_item(item, index, basis):
    matches = index.get(_match_key(item["medicine_key"], item["strength"], item["form"]), [])
    by_pharmacy = {}
    for row in matches:
        candidate = _price_candidate(row, item["quantity"], basis)
        current = by_pharmacy.get(candidate["pharmacy_id"])
        if current is None or _cheaper(candidate, current):
            by_pharmacy[candidate["pharmacy_id"]] = candidate
    candidates = sorted(by_pharmacy.values(), key=lambda c: (
        c["actual_disbursement_cents"] is None, c["actual_disbursement_cents"] or 0,
        c["pharmacy_id"], c["offer_id"]))
    computable = [c for c in candidates if c["actual_disbursement_cents"] is not None]
    status = "ok" if computable else ("missing" if not matches else "unpriced")
    return {**item, "status": status, "candidates": candidates}


def _multi_branch(items):
    picks = []
    total = 0
    for item in items:
        best = item["candidates"][0]
        total += best["actual_disbursement_cents"]
        picks.append({"medicine_key": item["medicine_key"], "pharmacy_id": best["pharmacy_id"],
                      "pharmacy": best["pharmacy"], "offer_id": best["offer_id"],
                      "actual_disbursement_cents": best["actual_disbursement_cents"]})
    return {"total_cents": total, "offers": picks}


def _single_branch(items):
    coverage = {}
    for idx, item in enumerate(items):
        for candidate in item["candidates"]:
            if candidate["actual_disbursement_cents"] is None:
                continue
            coverage.setdefault(candidate["pharmacy_id"], {})[idx] = candidate
    all_idx = set(range(len(items)))
    complete = {pid: picks for pid, picks in coverage.items() if set(picks) == all_idx}
    gaps = [{"pharmacy_id": pid, "pharmacy": next(iter(picks.values()))["pharmacy"],
             "covers": [items[i]["medicine_key"] for i in sorted(picks)],
             "missing": [items[i]["medicine_key"] for i in sorted(all_idx - set(picks))]}
            for pid, picks in coverage.items() if set(picks) != all_idx]
    if not complete:
        return None, sorted(gaps, key=lambda g: (-len(g["covers"]), g["pharmacy_id"]))
    best_pid = min(complete, key=lambda pid: (
        sum(c["actual_disbursement_cents"] for c in complete[pid].values()), pid))
    picks = complete[best_pid]
    offers = [{"medicine_key": items[i]["medicine_key"], "offer_id": picks[i]["offer_id"],
               "actual_disbursement_cents": picks[i]["actual_disbursement_cents"]} for i in sorted(picks)]
    return {"pharmacy_id": best_pid, "pharmacy": next(iter(picks.values()))["pharmacy"],
            "total_cents": sum(c["actual_disbursement_cents"] for c in picks.values()),
            "offers": offers}, []


def basket(args, store):
    items = _parse_items(args.items_path)
    dataset = store.get(args.dataset_id, "offers")
    index = {}
    for row in dataset["offers"]:
        if args.district and row["district"].casefold() != args.district.casefold():
            continue
        index.setdefault(_match_key(row["medicine_key"], row["strength"], row["form"]), []).append(row)

    resolved = [_resolve_item(item, index, args.basis) for item in items]
    all_ok = all(item["status"] == "ok" for item in resolved)
    multi_branch = _multi_branch(resolved) if all_ok else None
    single_branch, single_branch_gaps = _single_branch(resolved) if all_ok else (None, [])
    savings_cents = (single_branch["total_cents"] - multi_branch["total_cents"]
                     if single_branch and multi_branch else None)
    missing = [item["medicine_key"] for item in resolved if item["status"] == "missing"]

    result = {"kind": "basket", "schema_version": 1, "dataset_id": args.dataset_id,
              "basis": args.basis, "source": dataset["source"],
              "filters": {"district": args.district}, "items": resolved,
              "multi_branch": multi_branch, "single_branch": single_branch,
              "single_branch_gaps": single_branch_gaps, "savings_cents": savings_cents,
              "missing": missing}
    return {"result_id": store.put(result), "items": len(resolved), "missing": missing,
            "multi_branch_total_cents": multi_branch["total_cents"] if multi_branch else None,
            "single_branch_total_cents": single_branch["total_cents"] if single_branch else None,
            "savings_cents": savings_cents, "source": dataset["source"]}
