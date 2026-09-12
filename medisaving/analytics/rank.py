"""Owned by analytics team. No HTTP or presentation dependencies."""


def register(commands):
    command = commands.add_parser("rank", help="Rank comparable offers per medicine")
    command.add_argument("dataset_id")
    command.add_argument("--district")
    command.add_argument("--medicine", help="Filter to one medicine_key (exact, case-insensitive)")
    command.add_argument("--top", type=int, default=3)
    command.add_argument("--basis", choices=("unit", "pack"), default="unit")
    command.set_defaults(run=rank)


def rank(args, store):
    if not 1 <= args.top <= 10:
        raise ValueError("top must be between 1 and 10")
    dataset = store.get(args.dataset_id, "offers")
    groups = {}
    reasons = {"out_of_district": 0, "unpriced": 0, "unknown_pack": 0}
    field = f"{args.basis}_price_cents"
    medicine = getattr(args, "medicine", None)
    for row in dataset["offers"]:
        if args.district and row["district"].casefold() != args.district.casefold():
            reasons["out_of_district"] += 1
            continue
        if medicine and row["medicine_key"].casefold() != medicine.casefold():
            continue
        # Never mix strength, dosage form, or boxes of different sizes.
        if row.get(field) is None:
            reasons["unpriced"] += 1
            continue
        if args.basis == "pack" and row.get("pack_units") is None:
            reasons["unknown_pack"] += 1
            continue
        key = (row["medicine_key"], row["strength"], row["form"],
               row.get("pack_units") if args.basis == "pack" else None)
        groups.setdefault(key, []).append(row)
    selections = []
    for key, rows in sorted(groups.items()):
        branches = set()
        selected = []
        for row in sorted(rows, key=lambda r: (r[field], r["pharmacy_id"], r["offer_id"])):
            if row["pharmacy_id"] not in branches:
                selected.append(row)
                branches.add(row["pharmacy_id"])
            if len(selected) == args.top:
                break
        selections.append({"medicine_key": key[0], "strength": key[1], "form": key[2],
                           "pack_units": key[3], "offers": selected})
    skipped = reasons["unpriced"] + reasons["unknown_pack"]
    result = {"kind": "ranking", "schema_version": 1, "dataset_id": args.dataset_id,
              "basis": args.basis, "source": dataset["source"], "groups": selections,
              "excluded_unpriced_or_unknown_pack": skipped, "exclusion_reasons": reasons,
              "filters": {"district": args.district, "medicine": medicine, "top": args.top}}
    return {"result_id": store.put(result), "groups": len(selections),
            "selected": sum(len(g["offers"]) for g in selections),
            "excluded_unpriced_or_unknown_pack": skipped, "exclusion_reasons": reasons,
            "source": dataset["source"]}
