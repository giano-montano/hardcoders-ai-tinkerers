import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from medisaving.core import Store
from medisaving.ingest.commands import fetch
from medisaving.ingest.runtime.enrich import enrich
from medisaving.analytics import rank
from medisaving.ux import telegram
from tests.ingest.test_source import FakeClient


class RuntimeBridgeTests(unittest.TestCase):
    def test_exact_rank_filter_detail_join_and_ux(self):
        captured = json.loads((Path(__file__).parent / "fixtures/prices-recorded.json").read_text())
        with tempfile.TemporaryDirectory() as tmp, patch("medisaving.ingest.commands.Client", FakeClient):
            FakeClient.replies = [captured]
            store = Store(tmp)
            dataset_id = fetch(SimpleNamespace(ubigeo="150116", products=["1515:3:20mg"], pages=3, fresh=False, stats=False), store)["dataset_id"]
            args = SimpleNamespace(dataset_id=dataset_id, medicine="escitalopram", strength="20mg",
                                   form="tableta recubierta", district=None, top=1, basis="unit")
            selected = rank(args, store)
            original = store.get(selected["result_id"], "ranking")
            self.assertEqual(selected["selected"], 1)
            with patch("medisaving.ingest.runtime.enrich.detail", return_value={"presentacion": "Caja", "nombreFabricante": "Recorded fixture manufacturer", "detail_id": "detail-reference"}):
                joined = enrich(selected["result_id"], store)
            row = store.get(joined["result_id"], "ranking")["groups"][0]["offers"][0]
            old = original["groups"][0]["offers"][0]
            self.assertEqual((row["unit_price_cents"], row["pack_price_cents"]), (old["unit_price_cents"], old["pack_price_cents"]))
            self.assertEqual(row["presentation"], "Caja")
            self.assertEqual(store.get(selected["result_id"], "ranking"), original)
            rendered = telegram(SimpleNamespace(result_id=joined["result_id"], expand=False), store)
            self.assertIn("Presentation: Caja", "\n".join(rendered["interaction_responses"]["ux:details:o0"]["messages"]))
            args.form = "tableta sublingual"
            self.assertEqual(rank(args, store)["selected"], 0)

    def test_detail_failure_preserves_prices_and_exposes_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            result_id = store.put({"schema_version": 1, "kind": "ranking", "dataset_id": "unused",
                "source": {"warnings": []}, "groups": [{"offers": [{"offer_id": "unused", "unit_price_cents": 348}]}]})
            with patch("medisaving.ingest.runtime.enrich.detail", side_effect=ValueError("unavailable")):
                joined = enrich(result_id, store)
            result = store.get(joined["result_id"], "ranking")
            self.assertEqual(joined["detail_failures"], 1)
            self.assertIn("detail_unavailable", result["source"]["warnings"])
            self.assertEqual(result["groups"][0]["offers"][0]["unit_price_cents"], 348)
