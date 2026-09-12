"""Stable v1 contracts and local artifact storage. Coordinate changes here."""
import json
import os
from pathlib import Path
import re
import uuid


def validate_dataset(data):
    if data.get("schema_version") != 1 or data.get("kind") != "offers":
        raise ValueError("Expected offers schema_version 1")
    if not isinstance(data.get("offers"), list):
        raise ValueError("offers must be an array")
    source = data.get("source", {})
    for field in ("name", "fetched_at", "scope"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise ValueError(f"source.{field} is required")
    if type(source.get("complete")) is not bool:
        raise ValueError("source.complete must be explicit")
    seen = set()
    for row in data["offers"]:
        for field in ("offer_id", "medicine_key", "medicine", "strength", "form",
                      "pharmacy_id", "pharmacy", "district", "address"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Offer {field} is required")
        if row["offer_id"] in seen:
            raise ValueError("Duplicate offer_id")
        seen.add(row["offer_id"])
        if row.get("currency") != "PEN":
            raise ValueError("Only PEN is supported in v1")
        for field in ("unit_price_cents", "pack_price_cents", "pack_units"):
            value = row.get(field)
            if value is not None and (type(value) is not int or value <= 0):
                raise ValueError(f"{field} must be a positive integer or null")
        for field in ("laboratory", "phone", "reported_at", "presentation"):
            if row.get(field) is not None and not isinstance(row[field], str):
                raise ValueError(f"{field} must be a string or null")
    return data


class Store:
    def __init__(self, directory):
        self.root = Path(directory)

    def put(self, data):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        artifact_id = uuid.uuid4().hex
        path = self.root / f"{artifact_id}.json"
        payload = json.dumps(data, ensure_ascii=False, allow_nan=False)
        with open(path, "x", encoding="utf-8", opener=lambda p, f: os.open(p, f, 0o600)) as f:
            f.write(payload)
        return artifact_id

    def get(self, artifact_id, kind):
        if not re.fullmatch(r"[a-f0-9]{32}", artifact_id):
            raise ValueError("Invalid artifact ID")
        data = json.loads((self.root / f"{artifact_id}.json").read_text())
        if data.get("schema_version") != 1 or data.get("kind") != kind:
            raise ValueError(f"Expected {kind} artifact version 1")
        return data
