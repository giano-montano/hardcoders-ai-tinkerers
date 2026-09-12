"""Owned by UX team. Consume calculated artifacts; never recalculate prices."""


def register(areas):
    parser = areas.add_parser("ux", help="Render calculated results")
    commands = parser.add_subparsers(required=True)
    command = commands.add_parser("telegram", help="Render plain-text Telegram messages without sending")
    command.add_argument("result_id")
    command.set_defaults(run=telegram)


def money(value):
    return "not reported" if value is None else f"S/ {value // 100}.{value % 100:02d}"


def telegram(args, store):
    result = store.get(args.result_id, "ranking")
    messages = []
    for group in result["groups"]:
        for row in group["offers"]:
            text = (f"{row['medicine']} {row['strength']} · {row['form']}\n"
                    f"{row['pharmacy']} · {row['district']}\n{row['address']}\n"
                    f"Lab: {row.get('laboratory') or 'not reported'}\n"
                    f"Unit: {money(row.get('unit_price_cents'))} | "
                    f"Pack: {money(row.get('pack_price_cents'))} "
                    f"({row.get('pack_units') or '?'} units)\n"
                    f"Presentation: {row.get('presentation') or 'not reported'}\n"
                    f"Phone: {row.get('phone') or 'not reported'}\n"
                    f"Reported: {row.get('reported_at') or 'not reported'}")
            # Keep each chunk safely below Telegram's UTF-16 message limit.
            chunk = ""
            size = 0
            for char in text:
                width = len(char.encode('utf-16-le')) // 2
                if size + width > 3500:
                    messages.append(chunk)
                    chunk, size = "", 0
                chunk += char
                size += width
            if chunk:
                messages.append(chunk)
    source = result["source"]
    messages.append(("No comparable offers found. " if not result["groups"] else "") +
                    f"Source: {source['name']}. Coverage: {source['scope']}. "
                    f"Fetched: {source['fetched_at']}. " +
                    ("Partial results. " if not source["complete"] else "") +
                    "Confirm price and availability with the pharmacy.")
    artifact = {"kind": "telegram", "schema_version": 1,
                "result_id": args.result_id, "parse_mode": None, "messages": messages}
    return {"presentation_id": store.put(artifact), "parse_mode": None, "messages": messages}
