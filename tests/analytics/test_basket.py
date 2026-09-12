import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from medisaving.core import Store
from medisaving.analytics import basket
from tests.helpers import fixture


class BasketTests(unittest.TestCase):
    def calculate(self, data, items, basis="unit", district=None):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            items_path = Path(tmp) / "items.json"
            items_path.write_text(json.dumps(items))
            args = SimpleNamespace(dataset_id=store.put(data), items_path=str(items_path),
                                   district=district, basis=basis)
            return store.get(basket(args, store)["result_id"], "basket")

    def item(self, quantity=1, medicine_key="escitalopram", strength="20 mg", form="tablet"):
        return {"medicine_key": medicine_key, "strength": strength, "form": form, "quantity": quantity}

    def test_multi_branch_beats_single_branch_and_reports_savings(self):
        data = fixture()
        # A second medicine, cheapest at a branch that is expensive for the first one.
        second = {**data["offers"][0], "offer_id": "ibu-0", "medicine_key": "ibuprofeno",
                  "strength": "400 mg", "form": "tablet", "pharmacy_id": "synthetic-branch-0",
                  "unit_price_cents": 100, "pack_price_cents": 2000, "pack_units": 20}
        for pid, price in [("synthetic-branch-1", 300), ("synthetic-branch-2", 150)]:
            second_variant = {**second, "offer_id": f"ibu-{pid}", "pharmacy_id": pid,
                              "unit_price_cents": price}
            data["offers"].append(second_variant)
        data["offers"].append(second)
        items = [self.item(), self.item(medicine_key="ibuprofeno", strength="400 mg")]
        result = self.calculate(data, items)
        # escitalopram cheapest at branch-1 (180); ibuprofeno cheapest at branch-0 (100).
        self.assertEqual(result["multi_branch"]["total_cents"], 180 + 100)
        # Cheapest single branch covering both is branch-0 (230 + 100 = 330).
        self.assertEqual(result["single_branch"]["pharmacy_id"], "synthetic-branch-0")
        self.assertEqual(result["single_branch"]["total_cents"], 230 + 100)
        self.assertEqual(result["savings_cents"], (230 + 100) - (180 + 100))
        self.assertEqual(result["missing"], [])

    def test_pack_rounding_never_buys_a_partial_box(self):
        data = fixture()
        result = self.calculate(data, [self.item(quantity=10)], basis="pack")
        candidate = result["items"][0]["candidates"][0]
        self.assertEqual(candidate["packs_needed"], 1)
        self.assertTrue(candidate["rounded_up"])
        self.assertEqual(candidate["actual_disbursement_cents"], candidate["pack_total_cents"])

    def test_missing_medicine_excludes_totals_without_silent_drop(self):
        data = fixture()
        items = [self.item(), self.item(medicine_key="no-existe", strength="1 mg", form="tablet")]
        result = self.calculate(data, items)
        self.assertEqual(result["missing"], ["no-existe"])
        self.assertIsNone(result["multi_branch"])
        self.assertIsNone(result["single_branch"])
        self.assertIsNone(result["savings_cents"])
        self.assertEqual(result["items"][1]["status"], "missing")

    def test_duplicate_offers_at_same_branch_keep_cheapest_with_tie_break(self):
        data = fixture()
        extra = {**data["offers"][1], "offer_id": "demo-1b", "unit_price_cents": 180}
        data["offers"].append(extra)
        result = self.calculate(data, [self.item()])
        branch1 = next(c for c in result["items"][0]["candidates"]
                       if c["pharmacy_id"] == "synthetic-branch-1")
        self.assertEqual(branch1["offer_id"], "demo-1")  # Tie broken by offer_id, not duplicated.

    def test_strength_mismatch_is_never_treated_as_the_same_group(self):
        data = fixture()
        result = self.calculate(data, [self.item(strength="10 mg")])
        self.assertEqual(result["items"][0]["status"], "missing")

    def test_same_chain_different_branches_are_not_merged(self):
        data = fixture()
        for row in data["offers"]:
            row["pharmacy"] = "SAME CHAIN"  # branch-3 already has no unit price in the fixture
        items = [self.item(quantity=1)]
        result = self.calculate(data, items)
        candidates = {c["pharmacy_id"]: c for c in result["items"][0]["candidates"]}
        # Every branch is listed even though they share a chain name (never merged by pharmacy).
        self.assertEqual(set(candidates), {"synthetic-branch-0", "synthetic-branch-1",
                                           "synthetic-branch-2", "synthetic-branch-3"})
        # But the one without a usable price is never picked as computable.
        self.assertIsNone(candidates["synthetic-branch-3"]["actual_disbursement_cents"])
        self.assertEqual(result["items"][0]["status"], "ok")
