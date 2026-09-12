"""Telegram text presentation owned by the UX team.

This module renders already-ranked artifacts. It never sends Telegram messages,
calls HTTP, or recalculates prices.
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode


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


def _location_query(row: dict[str, Any]) -> str | None:
    """Build a branch search query without requiring the user's location."""
    fields = (row.get("pharmacy"), row.get("address"), row.get("district"), "Lima, Peru")
    values = [" ".join(str(value).split()) for value in fields if value is not None and str(value).strip()]
    return ", ".join(values) if values else None


def google_maps_url(row: dict[str, Any]) -> str | None:
    """Return a direct Maps search URL for a reported branch address."""
    query = _location_query(row)
    if not query or not row.get("address"):
        return None
    return f"https://www.google.com/maps/search/?{urlencode({'api': '1', 'query': query})}"


def offer_summary_text(row: dict[str, Any], position: int) -> str:
    """Keep the first screen short enough to scan comfortably on a phone."""
    return (
        f"Option {position}\n"
        f"Medicine: {display(row.get('medicine'))} · {display(row.get('strength'))} · {display(row.get('form'))}\n"
        f"Pharmacy: {display(row.get('pharmacy'))} ({display(row.get('district'))})\n"
        f"Box price: {money(row.get('pack_price_cents'))} · {display(row.get('pack_units'))} units\n"
        f"Address: {display(row.get('address'))}"
    )


def offer_detail_text(row: dict[str, Any], position: int) -> str:
    """Details are available on demand instead of crowding the first screen."""
    return (
        f"Option {position} — details\n"
        f"Medicine: {display(row.get('medicine'))} · {display(row.get('strength'))} · {display(row.get('form'))}\n"
        f"Pharmacy: {display(row.get('pharmacy'))} ({display(row.get('district'))})\n"
        f"Address: {display(row.get('address'))}\nLaboratory: {display(row.get('laboratory'))}\n"
        f"Unit price: {money(row.get('unit_price_cents'))} | Box price: {money(row.get('pack_price_cents'))} | "
        f"Units per box: {display(row.get('pack_units'))}\nPresentation: {display(row.get('presentation'))}\n"
        f"Phone: {display(row.get('phone'))} | Reported: {display(row.get('reported_at'))}"
    )


def _quantity_check(result: dict[str, Any], medicine_key: Any) -> dict[str, Any] | None:
    """Find optional, upstream-verified prescription metadata for one medicine."""
    for check in result.get("prescription_checks", []):
        if not isinstance(check, dict):
            continue
        if str(check.get("medicine_key", "")).casefold() == str(medicine_key).casefold():
            return check
    return None


def prescription_notice(row: dict[str, Any], check: dict[str, Any] | None) -> str | None:
    """Give a cautious purchase warning; never calculate or change a dose here."""
    if not check:
        return None
    if check.get("requires_pharmacist_verification") is True:
        return (
            "Pharmacist verification is needed before purchase. Please bring the original "
            "prescription and do not change the prescribed dose."
        )
    required = check.get("prescribed_units")
    pack_units = row.get("pack_units")
    confidence = check.get("quantity_confidence")
    if confidence == "low" and required is not None:
        return "We could not confirm the prescribed quantity. Please verify it with your pharmacist."
    if (confidence in (None, "high") and isinstance(required, int) and required > 0
            and isinstance(pack_units, int) and required > pack_units):
        if check.get("partial_dispensing_available") is True:
            ending = "Ask the pharmacist whether permitted partial dispensing is available."
        else:
            ending = "Please confirm with the pharmacist whether you need another box."
        return (
            f"Prescription check: this prescription appears to need {required} units; "
            f"this box contains {pack_units}. {ending} Do not change the prescribed dose."
        )
    return None


def offer_keyboard(row: dict[str, Any], card_id: str) -> list[list[dict[str, str]]]:
    """Telegram-ready, declarative controls for the delivery adapter."""
    first_row = []
    maps = google_maps_url(row)
    if maps:
        first_row.append({"text": "Open map", "url": maps})
    if row.get("phone"):
        first_row.append({"text": "Call pharmacy", "callback_data": f"ux:call:{card_id}"})
    keyboard = [first_row] if first_row else []
    keyboard.append([{"text": "More details", "callback_data": f"ux:details:{card_id}"}])
    return keyboard


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
            "Use the button below to see all options." if hidden_options else "")
    partial = " Coverage is partial for the stated scope." if not source.get("complete") else ""
    return (f"{prefix}{more}\nSource: {display(source.get('name'))}. Coverage: {display(source.get('scope'))}. "
            f"Fetched: {display(source.get('fetched_at'))}.{partial}\n"
            "Prices and availability can change. Please confirm with the pharmacy before you go.")


def _presentation(result_id: str, result: dict[str, Any], expand: bool) -> dict[str, Any]:
    started = time.perf_counter()
    messages, keyboards, interaction_responses, hidden_options = [], [], {}, 0
    card_number = 0
    for group in result["groups"]:
        offers = group.get("offers", [])
        visible = offers if expand else offers[:DEFAULT_OPTIONS_PER_MEDICINE]
        hidden_options += len(offers) - len(visible)
        check = _quantity_check(result, group.get("medicine_key"))
        for number, row in enumerate(visible, start=1):
            card_id = f"o{card_number}"
            messages.append(offer_summary_text(row, number))
            keyboards.append({"message_index": len(messages) - 1,
                              "inline_keyboard": offer_keyboard(row, card_id)})
            interaction_responses[f"ux:details:{card_id}"] = {
                "messages": [offer_detail_text(row, number)]
            }
            if row.get("phone"):
                interaction_responses[f"ux:call:{card_id}"] = {
                    "action": "call_pharmacy", "phone": str(row["phone"])
                }
            notice = prescription_notice(row, check)
            if notice:
                messages.append(notice)
                keyboards.append({"message_index": len(messages) - 1,
                                  "inline_keyboard": [[{
                                      "text": "Why this alert?",
                                      "callback_data": f"ux:quantity:{card_id}",
                                  }]]})
                interaction_responses[f"ux:quantity:{card_id}"] = {"messages": [notice]}
            card_number += 1
    messages.append(source_text(result["source"], bool(result["groups"]), hidden_options))
    footer_keyboard = []
    if hidden_options:
        footer_keyboard.append([{"text": "See all options", "callback_data": "ux:expand"}])
        interaction_responses["ux:expand"] = {"action": "render", "expand": True}
    footer_keyboard.append([{"text": "New prescription", "callback_data": "ux:new"}])
    interaction_responses["ux:new"] = {"action": "start_new_prescription"}
    keyboards.append({"message_index": len(messages) - 1, "inline_keyboard": footer_keyboard})
    chunks = [chunk for message in messages for chunk in split_telegram(message)]
    # Summaries are intentionally short, so a keyboard is attached to one message only.
    if len(chunks) != len(messages):
        keyboards = []
        interaction_responses = {}
    render_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"kind": "telegram", "schema_version": 1, "result_id": result_id,
            "parse_mode": None, "messages": chunks, "keyboards": keyboards,
            "interaction_responses": interaction_responses,
            "metrics": {"first_message_ms": render_ms, "render_ms": render_ms,
                        "output_utf8_bytes": sum(len(chunk.encode("utf-8")) for chunk in chunks)}}


def telegram(args, store):
    """Render Ranking v1 to text; artifact delivery remains a separate adapter."""
    result = store.get(args.result_id, "ranking")
    artifact = _presentation(args.result_id, result, getattr(args, "expand", False))
    return {"presentation_id": store.put(artifact), "parse_mode": None,
            "messages": artifact["messages"], "keyboards": artifact["keyboards"],
            "interaction_responses": artifact["interaction_responses"], "metrics": artifact["metrics"]}


def render_status(args, store):
    message = STATUS_MESSAGES[args.state]
    artifact = {"kind": "telegram", "schema_version": 1, "state": args.state,
                "parse_mode": None, "messages": [message]}
    return {"presentation_id": store.put(artifact), "state": args.state,
            "parse_mode": None, "messages": [message]}
