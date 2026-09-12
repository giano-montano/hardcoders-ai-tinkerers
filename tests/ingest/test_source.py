import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from medisaving.core import Store
from medisaving.ingest.commands import fetch, resolve, detail
from medisaving.ingest.normalize import positive


def raw(branch="demo-branch"):
    # Official response structure, with synthetic establishment/contact data.
    return {"codEstab": branch, "codProdE": 45457, "grupo": "1515", "codGrupoFF": "3",
            "concent": "20 mg", "ubicodigo": "150116", "nombreProducto": "ESCITALOPRAM",
            "nombreSustancia": "ESCITALOPRAM OXALATO", "nombreFormaFarmaceutica": "Comprimido Recubierto",
            "nombreComercial": "SYNTHETIC PHARMACY", "direccion": "SYNTHETIC ADDRESS",
            "distrito": "LINCE", "precio1": "104.30", "precio2": "3.48", "fracciones": 30,
            "nombreLaboratorio": "SYNTHETIC LAB", "telefono": None, "fecha": "25/08/2026"}


class FakeClient:
    replies = []

    def __init__(self, *a, **kw):
        self.requests = self.hits = 0
        self.index = 0

    def post(self, route, query):
        self.requests += 1
        reply = self.replies[self.index]
        self.index += 1
        if isinstance(reply, Exception):
            raise reply
        return reply, 1789236000


class SourceTests(unittest.TestCase):
    def run_fetch(self, replies, pages=3):
        with tempfile.TemporaryDirectory() as tmp, patch("medisaving.ingest.commands.Client", FakeClient):
            FakeClient.replies = replies
            store = Store(tmp)
            result = fetch(SimpleNamespace(ubigeo="150116", products=["1515:3:20mg"],
                                           pages=pages, fresh=False, stats=True), store)
            return result, store.get(result["dataset_id"], "offers")

    def test_source_ignores_page_size_and_returns_all(self):
        result, dataset = self.run_fetch([{"data": [raw(str(i)) for i in range(122)], "cantidad": 122}])
        self.assertTrue(result["complete"])
        self.assertEqual(result["stats"]["requests"], 1)
        self.assertEqual(dataset["offers"][0]["unit_price_cents"], 348)
        self.assertEqual(dataset["offers"][0]["pack_price_cents"], 10430)

    def test_repeated_page_cannot_claim_coverage(self):
        reply = {"data": [raw()], "cantidad": 2}
        result, _ = self.run_fetch([reply, reply])
        self.assertFalse(result["complete"])
        self.assertIn("repeated_page", result["warnings"])
        self.assertEqual(result["n"], 1)

    def test_network_failure_preserves_partial_rows(self):
        result, _ = self.run_fetch([{"data": [raw()], "cantidad": 2}, ValueError("timeout")])
        self.assertEqual(result["n"], 1)
        self.assertFalse(result["complete"])
        self.assertIn("source_error", result["warnings"])

    def test_pagination_deduplicates_overlap(self):
        result, _ = self.run_fetch([{"data": [raw("a")], "cantidad": 2},
                                    {"data": [raw("a"), raw("b")], "cantidad": 2}])
        self.assertTrue(result["complete"])
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["stats"]["duplicates"], 1)

    def test_empty_unknown_coverage_and_reported_zero(self):
        for total, complete in [(None, False), (0, True), (2, False)]:
            result, _ = self.run_fetch([{"data": None, "cantidad": total}])
            self.assertEqual(result["complete"], complete)

    def test_wrong_strength_location_and_money_rejected(self):
        for key, value in [("concent", "10mg"), ("ubicodigo", "150131"), ("precio1", "1.2345")]:
            row = raw()
            row[key] = value
            result, _ = self.run_fetch([{"data": [row], "cantidad": 1}])
            self.assertEqual(result["n"], 0)
            self.assertFalse(result["complete"])

    def test_unknown_unit_stays_unknown(self):
        row = raw()
        row["precio2"] = None
        result, dataset = self.run_fetch([{"data": [row], "cantidad": 1}])
        self.assertIsNone(dataset["offers"][0]["unit_price_cents"])

    def test_mixed_forms_are_preserved_and_flagged(self):
        first, second = raw("a"), raw("b")
        first["nombreFormaFarmaceutica"] = "Tableta Sublingual"
        second["nombreFormaFarmaceutica"] = "Tableta de Desintegración Oral"
        result, dataset = self.run_fetch([{"data": [first, second], "cantidad": 2}])
        self.assertIn("verify_offer_forms", result["warnings"])
        self.assertEqual([r["form"] for r in dataset["offers"]], [first["nombreFormaFarmaceutica"], second["nombreFormaFarmaceutica"]])

    def test_detail_reads_entity_without_overwriting_prices(self):
        with tempfile.TemporaryDirectory() as tmp, patch("medisaving.ingest.commands.Client", FakeClient):
            store = Store(tmp)
            original = {"schema_version": 1, "kind": "offers", "offers": [
                {"offer_id": "a:1", "source_product_id": "1", "pharmacy_id": "a", "unit_price_cents": 348}]}
            dataset_id = store.put(original)
            FakeClient.replies = [{"entidad": {"presentacion": "Caja", "laboratorio": "DEMO", "precio2": "9.99"}}]
            result = detail(SimpleNamespace(dataset_id=dataset_id, offer_id="a:1", fresh=False), store)
            self.assertEqual(result["presentacion"], "Caja")
            self.assertEqual(store.get(dataset_id, "offers"), original)

    def test_decimal_and_ambiguous_numeric_input(self):
        self.assertEqual(positive("0,25", cents=True), 25)
        for value in ["NaN", "Infinity", "1,234.56", True, -1, "0.001"]:
            with self.assertRaises(ValueError):
                positive(value, cents=True)

    def test_alias_resolution_preserves_sl_candidate_warning(self):
        with tempfile.TemporaryDirectory() as tmp, patch("medisaving.ingest.commands.Client", FakeClient):
            FakeClient.replies = [{"data": []}, {"data": [{"grupo": 1058, "codGrupoFF": "3",
                "concent": "0.25mg", "nombreProducto": "ZATRIX SL", "nombreFormaFarmaceutica": "Tableta - Capsula"}]}]
            result = resolve(SimpleNamespace(query="clonazepam", strength="0,25mg", sl=True, fresh=False), Store(tmp))
            self.assertEqual(result["candidates"][0][0], "1058:3:0.25mg")
            self.assertIn("SL_name_match_verify_offer_form", result["warnings"])
