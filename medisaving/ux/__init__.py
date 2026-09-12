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
        "📷 I could not read the prescription.\n\n"
        "Please send another photo in good light, with the medicine names and instructions fully visible."
    ),
    "missing_district": (
        "📍 Where are you in Lima?\n\n"
        "Tell me your district and I will look for nearby pharmacies. For example: Miraflores."
    ),
    "ambiguous_query": (
        "🔎 I found more than one possible medicine.\n\n"
        "Please check the name, strength, and form shown on your prescription."
    ),
    "no_results": (
        "😕 I could not find a matching option in this search.\n\n"
        "Try another district, or ask a pharmacist about local availability."
    ),
    "error": "⚠️ I could not prepare your result.\n\nPlease try again in a moment.",
    "recover": "✨ Ready when you are.\n\nSend another prescription photo to start a new search.",
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


def known(value: Any) -> str | None:
    """Return external data only when it is useful to show to a person."""
    if value is None or not str(value).strip():
        return None
    return " ".join(str(value).split())


def _price(value: int | None) -> str | None:
    return None if value is None else money(value)


def price_summary(row: dict[str, Any]) -> str:
    """Connect the per-box and per-unit values in one easy-to-read sentence."""
    box = _price(row.get("pack_price_cents"))
    unit = _price(row.get("unit_price_cents"))
    if box and unit:
        return f"💰 {box} per box · {unit} each"
    if box:
        return f"💰 {box} per box"
    if unit:
        return f"💰 {unit} each"
    return "💰 Price needs confirmation"


def pack_summary(row: dict[str, Any]) -> str | None:
    units = known(row.get("pack_units"))
    presentation = known(row.get("presentation"))
    if presentation:
        return f"📦 Box: {presentation}"
    if units:
        return f"📦 {units} per box"
    return None


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
    medicine = " · ".join(filter(None, (known(row.get("medicine")), known(row.get("strength")),
                                           known(row.get("form"))))) or "Medicine details unavailable"
    pharmacy = known(row.get("pharmacy")) or "Pharmacy details unavailable"
    district = known(row.get("district"))
    place = f"{pharmacy} · {district}" if district else pharmacy
    lines = [f"💊 OPTION {position}", medicine, f"🏪 {place}", price_summary(row)]
    if pack := pack_summary(row):
        lines.append(pack)
    if address := known(row.get("address")):
        lines.append(f"📍 {address}")
    return "\n\n".join(lines)


def offer_detail_text(row: dict[str, Any], position: int) -> str:
    """Details are available on demand instead of crowding the first screen."""
    medicine = " · ".join(filter(None, (known(row.get("medicine")), known(row.get("strength")),
                                           known(row.get("form"))))) or "Medicine details unavailable"
    lines = [f"ℹ️ OPTION {position} — DETAILS", f"💊 {medicine}"]
    if pharmacy := known(row.get("pharmacy")):
        district = known(row.get("district"))
        lines.append(f"🏪 {pharmacy}{f' · {district}' if district else ''}")
    if address := known(row.get("address")):
        lines.append(f"📍 {address}")
    lines.append(price_summary(row))
    if pack := pack_summary(row):
        lines.append(pack)
    if laboratory := known(row.get("laboratory")):
        lines.append(f"🏭 Laboratory: {laboratory}")
    if phone := known(row.get("phone")):
        lines.append(f"☎️ {phone}")
    if reported := known(row.get("reported_at")):
        lines.append(f"🕒 Price reported: {reported}")
    return "\n\n".join(lines)


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
            "⚠️ PHARMACIST CHECK\n\nThis medicine needs pharmacist verification before purchase. "
            "Bring the original prescription and do not change the prescribed dose."
        )
    required = check.get("prescribed_units")
    pack_units = row.get("pack_units")
    confidence = check.get("quantity_confidence")
    if confidence == "low" and required is not None:
        return "⚠️ QUICK CHECK\n\nI could not confirm the prescribed quantity. Please verify it with your pharmacist."
    if (confidence in (None, "high") and isinstance(required, int) and required > 0
            and isinstance(pack_units, int) and required > pack_units):
        if check.get("partial_dispensing_available") is True:
            ending = "Ask the pharmacist whether permitted partial dispensing is available."
        else:
            ending = "Please confirm with the pharmacist whether you need another box."
        return (
            f"⚠️ QUICK CHECK\n\nYour prescription appears to need {required} units. "
            f"This box has {pack_units}. {ending}\n\nDo not change the prescribed dose."
        )
    return None


def offer_keyboard(row: dict[str, Any], card_id: str) -> list[list[dict[str, str]]]:
    """Telegram-ready, declarative controls for the delivery adapter."""
    first_row = []
    maps = google_maps_url(row)
    if maps:
        first_row.append({"text": "🗺️ Open map", "url": maps})
    if row.get("phone"):
        first_row.append({"text": "☎️ Call pharmacy", "callback_data": f"ux:call:{card_id}"})
    keyboard = [first_row] if first_row else []
    keyboard.append([{"text": "ℹ️ More details", "callback_data": f"ux:details:{card_id}"}])
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
    lines = []
    if not has_results:
        lines.append(STATUS_MESSAGES["no_results"])
    elif hidden_options:
        lines.append(f"✨ I found {hidden_options} more option{'s' if hidden_options != 1 else ''}. "
                     "Tap below to see them.")
    scope = known(source.get("scope"))
    fetched = known(source.get("fetched_at"))
    if scope:
        lines.append(f"🔎 Search area: {scope}.")
    if fetched:
        lines.append(f"🕒 Last checked: {fetched}.")
    if not source.get("complete"):
        lines.append("ℹ️ This search may not include every pharmacy.")
    lines.append("🔔 Before you go, call the pharmacy to confirm the price and availability.")
    return "\n\n".join(lines)


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
                                      "text": "ℹ️ Why this alert?",
                                      "callback_data": f"ux:quantity:{card_id}",
                                  }]]})
                interaction_responses[f"ux:quantity:{card_id}"] = {"messages": [notice]}
            card_number += 1
    messages.append(source_text(result["source"], bool(result["groups"]), hidden_options))
    footer_keyboard = []
    if hidden_options:
        footer_keyboard.append([{"text": "🔎 See all options", "callback_data": "ux:expand"}])
        interaction_responses["ux:expand"] = {"action": "render", "expand": True}
    footer_keyboard.append([{"text": "📷 New prescription", "callback_data": "ux:new"}])
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
