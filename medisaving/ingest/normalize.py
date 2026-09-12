"""Source normalization only. No ranking, basket arithmetic or price inference."""
from decimal import Decimal, InvalidOperation
from copy import deepcopy
import re
import unicodedata


PROFILE = "text-v1"


def text(value):
    if not isinstance(value, str):
        raise ValueError("Identity fields must be strings")
    return unicodedata.normalize("NFC", " ".join(value.casefold().split()))


def strength(value):
    value = re.sub(r"\s+", "", str(value)).lower().replace(",", ".")
    def number(match):
        result = format(Decimal(match.group()), "f")
        return result.rstrip("0").rstrip(".") if "." in result else result
    return re.sub(r"\d+(?:\.\d*)?|\.\d+", number, value)


def canonical_offer(row):
    """Normalize both import/fetch identically; preserve source evidence once."""
    result = deepcopy(row)
    key = text(row["medicine_key"])
    fallback = key.startswith("digemid:")
    if fallback and not re.fullmatch(r"digemid:[0-9]+", key):
        raise ValueError("Invalid source-group identity")
    original = result.setdefault("source_values", {
        "substance": None if fallback else row["medicine_key"],
        "strength": row["strength"], "form": row["form"],
    })
    if not isinstance(original, dict) or any(
        value is not None and not isinstance(value, str) for value in original.values()
    ):
        raise ValueError("source_values must contain strings or null")
    result.update(medicine_key=key, strength=strength(row["strength"]), form=text(row["form"]),
                  identity_status="source_group_only" if fallback else "substance_reported")
    return result


def canonical_import(dataset):
    result = deepcopy(dataset)
    source = result["source"]
    if source.get("normalization") not in (None, PROFILE):
        raise ValueError("Unsupported normalization profile")
    warnings = source.get("warnings", ["diagnostics_unavailable"])
    if not isinstance(warnings, list) or not all(isinstance(w, str) for w in warnings):
        raise ValueError("source.warnings must be an array of strings")
    source.update(normalization=PROFILE, warnings=sorted(set(warnings)))
    # These counters describe this import; preserve prior diagnostics when present.
    for field in ("rejected_rows", "duplicate_rows"):
        value = source.setdefault(field, 0)
        if type(value) is not int or value < 0:
            raise ValueError(f"source.{field} must be a nonnegative integer")
    if source["rejected_rows"] or "conflicting_duplicate" in warnings:
        source["complete"] = False
    result["offers"] = [canonical_offer(row) for row in result["offers"]]
    return result


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
    substance = row.get("nombreSustancia")
    if substance is not None and not isinstance(substance, str):
        raise ValueError("Invalid source substance")
    result = {
        "offer_id": f"{branch}:{code}", "medicine_key": substance if substance and substance.strip() else f"digemid:{product['group']}",
        "medicine": row.get("nombreProducto"), "strength": row.get("concent"),
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
        "source_values": {"substance": substance, "strength": row.get("concent"),
                          "form": row.get("nombreFormaFarmaceutica")},
    }
    for key, value in result.items():
        if isinstance(value, str):
            result[key] = value.strip()
    return canonical_offer(result)
