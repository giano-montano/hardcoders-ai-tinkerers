"""Telegram text presentation owned by the UX team.

This module renders already-ranked artifacts. It never sends Telegram messages,
calls HTTP, or recalculates prices.
"""

from __future__ import annotations

import time
from typing import Any


TELEGRAM_SAFE_UTF16 = 3500
DEFAULT_OPTIONS_PER_MEDICINE = 2

STATUS_MESSAGES = {
    "unreadable_photo": (
        "I could not read the prescription photo. Please send a new, well-lit photo "
        "with the medicine names and directions fully visible."
    ),
    "missing_district": (
        "Please tell me your district in Lima so I can look for nearby options."
    ),
    "ambiguous_query": (
        "I found more than one possible medicine. Please confirm the exact name, "
        "strength, and form shown on your prescription."
    ),
    "no_results": (
        "No comparable offers were found for this search. You can try another district "
        "or ask a pharmacist to confirm local availability."
    ),
    "error": "Something went wrong while preparing your result. Please try again.",
    "recover": "You can send another prescription photo or start a new search when you are ready.",
}


def register(areas):
    parser = areas.add_parser("ux", help="Render calculated results and explicit conversation states")
    commands = parser.add_subparsers(required=True)
    command = commands.add_parser("telegram", help="Render plain-text Telegram messages without sending")
    command.add_argument("result_id")
    command.add_argument("--expand", action="store_true",
                         help="Include every ranked option instead of the first two per medicine")
    command.set_defaults(run=telegram)
    status = commands.add_parser("status", help="Render a predefined recovery or progress message")
    status.add_argument("state", choices=tuple(STATUS_MESSAGES))
    status.set_defaults(run=render_status)


def money(value: int | None) -> str:
    return "not reported" if value is None else f"S/ {value // 100}.{value % 100:02d}"


def display(value: Any) -> str:
    """Make external data one readable line without changing its content."""
    if value is None or not str(value).strip():
        return "not reported"
    return " ".join(str(value).split())


def offer_text(row: dict[str, Any], position: int) -> str:
    """One complete, scannable option. Labels remain even for missing values."""
    return (
        f"Option {position}\n"
        f"Medicine: {display(row.get('medicine'))} · {display(row.get('strength'))} · {display(row.get('form'))}\n"
        f"Pharmacy: {display(row.get('pharmacy'))} ({display(row.get('district'))})\n"
        f"Address: {display(row.get('address'))}\nLaboratory: {display(row.get('laboratory'))}\n"
        f"Unit price: {money(row.get('unit_price_cents'))} | Box price: {money(row.get('pack_price_cents'))} | "
        f"Units per box: {display(row.get('pack_units'))}\nPresentation: {display(row.get('presentation'))}\n"
        f"Phone: {display(row.get('phone'))} | Reported: {display(row.get('reported_at'))}"
    )


def split_telegram(text: str) -> list[str]:
    """Split safely by Telegram's UTF-16 limit, preferring line boundaries."""
    chunks, current, units = [], "", 0
    for line in text.splitlines(keepends=True) or [text]:
        for character in line:
            width = len(character.encode("utf-16-le")) // 2
            if current and units + width > TELEGRAM_SAFE_UTF16:
                chunks.append(current.rstrip())
                current, units = "", 0
            current += character
            units += width
    if current:
        chunks.append(current.rstrip())
    return chunks or [""]


def source_text(source: dict[str, Any], has_results: bool, hidden_options: int) -> str:
    prefix = STATUS_MESSAGES["no_results"] if not has_results else ""
    more = (f" {hidden_options} more comparable option{' is' if hidden_options == 1 else 's are'} available. "
            "Ask to see all options." if hidden_options else "")
    partial = " Coverage is partial for the stated scope." if not source.get("complete") else ""
    return (f"{prefix}{more}\nSource: {display(source.get('name'))}. Coverage: {display(source.get('scope'))}. "
            f"Fetched: {display(source.get('fetched_at'))}.{partial}\n"
            "Prices and availability can change. Please confirm with the pharmacy before you go.")


def _presentation(result_id: str, result: dict[str, Any], expand: bool) -> dict[str, Any]:
    started = time.perf_counter()
    messages, hidden_options = [], 0
    for group in result["groups"]:
        offers = group.get("offers", [])
        visible = offers if expand else offers[:DEFAULT_OPTIONS_PER_MEDICINE]
        hidden_options += len(offers) - len(visible)
        messages.extend(offer_text(row, number) for number, row in enumerate(visible, start=1))
    messages.append(source_text(result["source"], bool(result["groups"]), hidden_options))
    chunks = [chunk for message in messages for chunk in split_telegram(message)]
    render_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"kind": "telegram", "schema_version": 1, "result_id": result_id,
            "parse_mode": None, "messages": chunks,
            "metrics": {"first_message_ms": render_ms, "render_ms": render_ms,
                        "output_utf8_bytes": sum(len(chunk.encode("utf-8")) for chunk in chunks)}}


def telegram(args, store):
    """Render Ranking v1 to text; artifact delivery remains a separate adapter."""
    result = store.get(args.result_id, "ranking")
    artifact = _presentation(args.result_id, result, getattr(args, "expand", False))
    return {"presentation_id": store.put(artifact), "parse_mode": None,
            "messages": artifact["messages"], "metrics": artifact["metrics"]}


def render_status(args, store):
    message = STATUS_MESSAGES[args.state]
    artifact = {"kind": "telegram", "schema_version": 1, "state": args.state,
                "parse_mode": None, "messages": [message]}
    return {"presentation_id": store.put(artifact), "state": args.state,
            "parse_mode": None, "messages": [message]}
