import tempfile
from types import SimpleNamespace
import unittest
from medisaving.core import Store
from medisaving.analytics import rank
from tests.helpers import fixture


class RankTests(unittest.TestCase):
    def calculate(self, data, basis="unit"):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            args = SimpleNamespace(dataset_id=store.put(data), district=None, top=3, basis=basis)
            return store.get(rank(args, store)["result_id"], "ranking")

    def test_exact_prices_unknown_unit_and_duplicate_branch(self):
        data = fixture()
        data["offers"][0]["pharmacy_id"] = data["offers"][1]["pharmacy_id"]
        result = self.calculate(data)
        self.assertEqual([r["unit_price_cents"] for r in result["groups"][0]["offers"]], [180, 200])
        self.assertEqual(result["excluded_unpriced_or_unknown_pack"], 1)

    def test_strength_form_and_pack_size_are_not_mixed(self):
        data = fixture()
        data["offers"][0]["strength"] = "10 mg"
        data["offers"][2]["form"] = "sublingual tablet"
        self.assertEqual(len(self.calculate(data)["groups"]), 3)
        data = fixture()
        data["offers"][0]["pack_units"] = 10
        self.assertEqual(len(self.calculate(data, "pack")["groups"]), 2)
        data["offers"][0]["pack_units"] = None
        self.assertEqual(self.calculate(data, "pack")["excluded_unpriced_or_unknown_pack"], 1)
