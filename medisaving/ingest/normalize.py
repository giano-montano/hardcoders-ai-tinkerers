"""Source normalization only. No ranking, basket arithmetic or price inference."""
from decimal import Decimal, InvalidOperation
import re


def strength(value):
    return re.sub(r"\s+", "", str(value)).lower().replace(",", ".")


def positive(value, cents=False):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("Invalid numeric value")
    try:
        number = Decimal(str(value).replace(",", "."))
        if cents:
            number *= 100
        if not number.is_finite() or number < 0 or number != number.to_integral_value():
            raise ValueError("Ambiguous numeric value")
        return int(number) or None
    except InvalidOperation:
        raise ValueError("Invalid numeric value") from None


def offer(row, product, ubigeo):
    if str(row.get("ubicodigo")) != ubigeo:
        raise ValueError("Location mismatch")
    if str(row.get("grupo")) != product["group"] or str(row.get("codGrupoFF")) != product["ff"]:
        raise ValueError("Product group mismatch")
    if strength(row.get("concent", "")) != product["strength"]:
        raise ValueError("Strength mismatch")
    branch, code = row.get("codEstab"), row.get("codProdE")
    if branch is None or code is None:
        raise ValueError("Missing source identity")
    result = {
        "offer_id": f"{branch}:{code}", "medicine_key": str(row.get("nombreSustancia") or f"digemid:{product['group']}").strip(),
        "medicine": row.get("nombreProducto"), "strength": product["strength"],
        "form": row.get("nombreFormaFarmaceutica"), "pharmacy_id": str(branch),
        "pharmacy": row.get("nombreComercial"), "district": row.get("distrito"),
        "address": row.get("direccion"), "currency": "PEN",
        "unit_price_cents": positive(row.get("precio2"), cents=True),
        "pack_price_cents": positive(row.get("precio1"), cents=True),
        "pack_units": positive(row.get("fracciones")),
        "laboratory": row.get("nombreLaboratorio"), "phone": row.get("telefono"),
        "reported_at": row.get("fecha"), "presentation": row.get("presentacion"),
        "source_product_id": str(code), "source_group": product["group"],
        "source_form_group": product["ff"], "ubigeo": ubigeo,
    }
    for key, value in result.items():
        if isinstance(value, str):
            result[key] = value.strip()
    return result
