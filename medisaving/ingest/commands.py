import hashlib
import json
from datetime import datetime, timezone
import re
import time
import unicodedata

from ..core import validate_dataset
from .client import Client
from .normalize import PROFILE, offer, strength, text as canonical_text


def view(args, store):
    if not 1 <= args.limit <= 5 or args.offset < 0:
        raise ValueError("Read limit must be 1–5; offset must be nonnegative")
    product = parse_product(args.product)
    dataset = store.get(args.dataset_id, "offers")
    form = canonical_text(args.form) if args.form else None
    fields = ("offer_id", "medicine", "strength", "form", "identity_status", "medicine_key",
              "pharmacy", "district", "address", "laboratory", "unit_price_cents",
              "pack_price_cents", "pack_units", "phone", "reported_at", "presentation")
    selected = []
    index = 0
    more = False
    for row in dataset["offers"]:
        if (row.get("source_group"), row.get("source_form_group"), row.get("strength")) != (
            product["group"], product["ff"], product["strength"]):
            continue
        if form and canonical_text(row["form"]) != form:
            continue
        if index >= args.offset:
            if len(selected) == args.limit:
                more = True
                break
            selected.append({key: row.get(key) for key in fields})
        index += 1
    source = dataset["source"]
    return {"offers": selected, "next": args.offset + len(selected) if more else None,
            "order": "source", "complete": source["complete"],
            "fetched_at": source["fetched_at"], "warnings": source.get("warnings", ["diagnostics_unavailable"])}

# Search fallbacks observed in the completed official-portal session.
# These are query hints, not clinical substitution rules.
ALIASES = {"aripiprazol": "AZYMOL", "clonazepam": "ZATRIX"}


def district(args, store):
    if not re.fullmatch(r"[0-9]{4}", args.province):
        raise ValueError("Province must be four digits (department + province)")
    def normalized(text):
        return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))
    client = Client(store.root, ttl=86400)
    data, _ = client.post("parametro/distritos", {"codigo": args.province[2:], "codigoDos": args.province[:2]})
    rows = data.get("data")
    if not isinstance(rows, list):
        raise ValueError("Invalid district data")
    matches = [[r["codigo"], r["descripcion"]] for r in rows
               if normalized(args.query) in normalized(r["descripcion"])]
    return {"districts": matches[:10], **({"warnings": ["truncated_refine_query"]} if len(matches) > 10 else {})}


def product_id(row):
    return f"{row['grupo']}:{row['codGrupoFF']}:{strength(row['concent'])}"


def parse_product(value):
    parts = value.split(":")
    if len(parts) != 3 or not all(re.fullmatch(r"[0-9]+", p) for p in parts[:2]):
        raise ValueError("Product ID: GROUP:FORM:STRENGTH; use ingest r")
    if not re.fullmatch(r"[a-zA-Z0-9.%/+-]+", parts[2]):
        raise ValueError("Invalid strength in product ID")
    return {"group": parts[0], "ff": parts[1], "strength": strength(parts[2])}


def resolve(args, store):
    client = Client(store.root, ttl=0 if args.fresh else 86400)
    query = args.query.strip()
    if not 1 <= len(query) <= 100:
        raise ValueError("Query must contain 1–100 characters")
    rows = []
    warnings = []
    for term in dict.fromkeys([query, ALIASES.get(query.casefold(), query)]):
        data, _ = client.post("producto/autocompleteciudadano", {
            "nombreProducto": term, "pagina": 1, "tamanio": 100, "tokenGoogle": ""})
        found = data.get("data")
        if found is not None and not isinstance(found, list):
            raise ValueError("Invalid autocomplete data")
        rows.extend(found or [])
    matches = {}
    for row in rows:
        if not isinstance(row, dict) or not all(row.get(k) is not None for k in ("grupo", "codGrupoFF", "concent", "nombreProducto")):
            warnings.append("invalid_candidate")
            continue
        if args.strength and strength(row.get("concent")) != strength(args.strength):
            continue
        if args.sl and not re.search(r"\bSL\b|SUBLING", row.get("nombreProducto", ""), re.I):
            continue
        key = product_id(row)
        matches[key] = [key, row["nombreProducto"], row.get("nombreFormaFarmaceutica")]
    if not matches:
        warnings.append("no_match")
    if args.sl:
        warnings.append("SL_name_match_verify_offer_form")
    output = {"candidates": list(matches.values())[:10]}
    if len(matches) > 10:
        warnings.append("truncated_refine_query")
    if warnings:
        output["warnings"] = warnings
    return output


def fetch(args, store):
    if not re.fullmatch(r"[0-9]{6}", args.ubigeo):
        raise ValueError("A six-digit district ubigeo is required")
    if not 1 <= len(args.products) <= 10 or not 1 <= args.pages <= 20:
        raise ValueError("Limit: 10 products, 1–20 pages each")
    products = [parse_product(p) for p in dict.fromkeys(args.products)]
    start = time.monotonic()
    client = Client(store.root, ttl=0 if args.fresh else 900)
    rows, timestamps, warnings, coverage = [], [], [], []
    for product in products:
        seen_pages, collected = set(), []
        complete, total = False, None
        for page in range(1, args.pages + 1):
            query = {"codigoProducto": int(product["group"]), "codGrupoFF": product["ff"],
                     "concent": product["strength"], "codigoDepartamento": args.ubigeo[:2],
                     "codigoProvincia": args.ubigeo[2:4], "codigoUbigeo": args.ubigeo,
                     "codTipoEstablecimiento": None, "catEstablecimiento": None,
                     "nombreEstablecimiento": None, "nombreLaboratorio": None, "nombreProducto": None,
                     "tamanio": 100, "pagina": page, "tokenGoogle": ""}
            try:
                data, stamp = client.post("preciovista/ciudadano", query)
                timestamps.append(stamp)
                batch = data.get("data")
                if batch is None:
                    batch = []
                if not isinstance(batch, list) or not all(isinstance(row, dict) for row in batch):
                    raise ValueError("Invalid price data")
                reported_total = data.get("cantidad")
                if type(reported_total) is int and reported_total >= 0:
                    if total is not None and total != reported_total:
                        warnings.append("source_changed_during_pagination")
                        break
                    total = reported_total
                fingerprint = hashlib.sha256(json.dumps(batch, sort_keys=True).encode()).hexdigest()
                if batch and fingerprint in seen_pages:
                    warnings.append("repeated_page")
                    break
                seen_pages.add(fingerprint)
                collected.extend(batch)
                unique = {(str(r.get("codEstab")), str(r.get("codProdE"))) for r in collected}
                if total is not None and len(unique) >= total:
                    complete = len(unique) == total
                    break
                if not batch:
                    # An empty page without a reported total is inconclusive.
                    complete = total is not None and len(unique) == total
                    break
            except (ValueError, OSError, TypeError, KeyError):
                warnings.append("source_error")
                break
        rows.extend((row, product) for row in collected)
        coverage.append({"product": product, "rows": len(collected), "total": total, "complete": complete})
        if not complete:
            warnings.append("partial")
    normalized, rejected, duplicates = {}, 0, 0
    source = {"name": "DIGEMID OPM", "fetched_at": datetime.fromtimestamp(min(timestamps) if timestamps else time.time(), timezone.utc).isoformat(),
              "scope": f"ubigeo={args.ubigeo};products={','.join(dict.fromkeys(args.products))}",
              "complete": all(c["complete"] for c in coverage), "coverage": coverage}
    for row, product in rows:
        try:
            item = offer(row, product, args.ubigeo)
            validate_dataset({"schema_version": 1, "kind": "offers", "source": source, "offers": [item]})
            if item["offer_id"] in normalized:
                duplicates += 1
                if normalized[item["offer_id"]] != item:
                    warnings.append("conflicting_duplicate")
                    source["complete"] = False
                continue
            normalized[item["offer_id"]] = item
        except (ValueError, TypeError, KeyError, AttributeError):
            rejected += 1
    if rejected:
        source["complete"] = False
        warnings.append("rejected_rows")
    forms = {}
    for item in normalized.values():
        forms.setdefault((item["source_group"], item["strength"]), set()).add(item["form"])
    if any(len(values) > 1 for values in forms.values()):
        warnings.append("verify_offer_forms")
    source.update(normalization=PROFILE, warnings=sorted(set(warnings)),
                  rejected_rows=rejected, duplicate_rows=duplicates)
    dataset = {"schema_version": 1, "kind": "offers", "source": source,
               "offers": list(normalized.values())}
    validate_dataset(dataset)
    dataset_id = store.put(dataset)
    stats = {"schema_version": 1, "kind": "ingest_stats", "dataset_id": dataset_id,
             "requests": client.requests, "cache_hits": client.hits,
             "ms": round((time.monotonic() - start) * 1000), "rejected": rejected,
             "duplicates": duplicates, "warnings": sorted(set(warnings)), "coverage": coverage}
    stats_id = store.put(stats)
    output = {"dataset_id": dataset_id, "n": len(normalized), "complete": source["complete"]}
    if warnings:
        output["warnings"] = sorted(set(warnings))
    if args.stats:
        output["stats"] = {k: stats[k] for k in ("requests", "cache_hits", "ms", "rejected", "duplicates")}
        output["stats_id"] = stats_id
    return output


def detail(args, store):
    dataset = store.get(args.dataset_id, "offers")
    rows = [r for r in dataset["offers"] if r["offer_id"] == args.offer_id]
    if not rows:
        raise ValueError("Offer not found in dataset")
    row = rows[0]
    client = Client(store.root, ttl=0 if args.fresh else 900)
    data, stamp = client.post("precioproducto/obtener", {
        "codigoProducto": row["source_product_id"], "codEstablecimiento": row["pharmacy_id"], "tokenGoogle": ""})
    entity = data.get("entidad")
    if not isinstance(entity, dict):
        raise ValueError("Missing offer detail")
    fields = ("presentacion", "laboratorio", "nombreFabricante", "registroSanitario",
              "condicionVenta", "telefono", "direccion", "distrito", "horarioAtencion")
    result = {"schema_version": 1, "kind": "offer_detail", "dataset_id": args.dataset_id,
              "offer_id": args.offer_id, "fetched_at": datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
              "detail": {k: entity.get(k) for k in fields}}
    return {"detail_id": store.put(result), **result["detail"]}
