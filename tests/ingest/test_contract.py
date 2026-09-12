import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from medisaving.core import Store
from medisaving.ingest import import_offers
from medisaving.ingest.commands import fetch
from medisaving.ingest.normalize import canonical_import, canonical_offer, strength
from medisaving.analytics import rank
from tests.helpers import fixture
from tests.ingest.test_source import FakeClient, raw


class ContractTests(unittest.TestCase):
    def test_strength_canonical_decimal_without_unit_conversion(self):
        for original, expected in [("020,00 MG", "20mg"), ("0,250 mg", "0.25mg"),
                                   (".5 MG", "0.5mg"), ("1000 mcg", "1000mcg"),
                                   ("20 mg / 1 mL", "20mg/1ml")]:
            self.assertEqual(strength(original), expected)

    def test_normalization_is_idempotent_preserves_evidence_and_salts(self):
        dataset = fixture()
        row = dataset["offers"][0]
        row.update(medicine_key=" ESCITALOPRAM  OXALATO ", strength="020,00 MG",
                   form=" Tableta  Recubierta ")
        normalized = canonical_import(dataset)
        self.assertEqual(canonical_import(normalized), normalized)
        item = normalized["offers"][0]
        self.assertEqual(item["medicine_key"], "escitalopram oxalato")
        self.assertEqual(item["strength"], "20mg")
        self.assertEqual(item["source_values"]["strength"], "020,00 MG")
        self.assertEqual(row["strength"], "020,00 MG")  # Caller input untouched.
        other = canonical_offer({**row, "medicine_key": "ESCITALOPRAM"})
        self.assertNotEqual(item["medicine_key"], other["medicine_key"])

    def test_unknown_substance_and_legacy_diagnostics_are_explicit(self):
        dataset = fixture()
        dataset["offers"][0]["medicine_key"] = "digemid:1515"
        result = canonical_import(dataset)
        self.assertEqual(result["offers"][0]["identity_status"], "source_group_only")
        self.assertIsNone(result["offers"][0]["source_values"]["substance"])
        self.assertEqual(result["source"]["warnings"], ["diagnostics_unavailable"])

    def test_whitespace_only_source_substance_uses_group_fallback(self):
        from medisaving.ingest.normalize import offer
        row = raw()
        row["nombreSustancia"] = "  "
        result = offer(row, {"group": "1515", "ff": "3", "strength": "20mg"}, "150116")
        self.assertEqual(result["medicine_key"], "digemid:1515")
        self.assertEqual(result["identity_status"], "source_group_only")
        self.assertEqual(result["source_values"]["substance"], "  ")

    def test_future_profile_or_invalid_diagnostics_not_silently_reinterpreted(self):
        for field, value in [("normalization", "text-v2"), ("warnings", "partial"), ("rejected_rows", -1)]:
            dataset = fixture()
            dataset["source"][field] = value
            with self.assertRaises(ValueError):
                canonical_import(dataset)

    def test_source_diagnostics_survive_fetch_and_rank(self):
        bad = raw("bad")
        bad["precio1"] = "ambiguous"
        with tempfile.TemporaryDirectory() as tmp, patch("medisaving.ingest.commands.Client", FakeClient):
            FakeClient.replies = [{"data": [raw("ok"), bad], "cantidad": 2}]
            store = Store(tmp)
            response = fetch(SimpleNamespace(ubigeo="150116", products=["1515:3:20mg"], pages=3, fresh=False, stats=False), store)
            dataset = store.get(response["dataset_id"], "offers")
            self.assertEqual(dataset["source"]["rejected_rows"], 1)
            self.assertIn("rejected_rows", dataset["source"]["warnings"])
            self.assertTrue(dataset["source"]["coverage"][0]["complete"])
            self.assertFalse(dataset["source"]["complete"])
            ranked = rank(SimpleNamespace(dataset_id=response["dataset_id"], district=None, top=3, basis="unit"), store)
            self.assertEqual(store.get(ranked["result_id"], "ranking")["source"], dataset["source"])

    def test_recorded_fetch_and_import_share_identity_in_rank(self):
        captured = json.loads((Path(__file__).parent / "fixtures/prices-recorded.json").read_text())
        with tempfile.TemporaryDirectory() as tmp, patch("medisaving.ingest.commands.Client", FakeClient):
            FakeClient.replies = [captured]
            store = Store(tmp)
            response = fetch(SimpleNamespace(ubigeo="150116", products=["1515:3:20mg"], pages=3, fresh=False, stats=False), store)
            fetched = store.get(response["dataset_id"], "offers")
            self.assertEqual(response["n"], len(captured["data"]))
            self.assertEqual(fetched["source"]["normalization"], "text-v1")
            original = fetched["offers"][0]
            variant = {**original, "offer_id": "synthetic-other", "pharmacy_id": "000OTHER",
                       "medicine_key": original["medicine_key"].upper(), "strength": "020,00 MG",
                       "form": "  " + original["form"].upper() + "  "}
            # Import boundary normalizes a legacy-format offer alongside fetch output.
            fetched["offers"].append(variant)
            path = Path(tmp) / "input.json"
            path.write_text(json.dumps(fetched))
            imported = import_offers(SimpleNamespace(path=str(path)), store)
            result = rank(SimpleNamespace(dataset_id=imported["dataset_id"], district=None, top=10, basis="unit"), store)
            groups = store.get(result["result_id"], "ranking")["groups"]
            group = next(g for g in groups if any(r["offer_id"] == "synthetic-other" for r in g["offers"]))
            self.assertEqual({r["offer_id"] for r in group["offers"]}, {original["offer_id"], "synthetic-other"})
            self.assertEqual(sum(len(g["offers"]) for g in groups), len(captured["data"]) + 1)

    def test_fetch_directly_consumed_by_rank(self):
        captured = json.loads((Path(__file__).parent / "fixtures/prices-recorded.json").read_text())
        with tempfile.TemporaryDirectory() as tmp, patch("medisaving.ingest.commands.Client", FakeClient):
            FakeClient.replies = [captured]
            store = Store(tmp)
            response = fetch(SimpleNamespace(ubigeo="150116", products=["1515:3:20mg"], pages=3, fresh=False, stats=False), store)
            result = rank(SimpleNamespace(dataset_id=response["dataset_id"], district=None, top=3, basis="pack"), store)
            ranked = store.get(result["result_id"], "ranking")
            self.assertEqual(result["selected"], len(captured["data"]))
            self.assertTrue(all(g["strength"] == "20mg" for g in ranked["groups"]))
            self.assertTrue(all(g["pack_units"] == 30 for g in ranked["groups"]))
