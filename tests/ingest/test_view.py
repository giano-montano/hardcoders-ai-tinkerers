import tempfile
from types import SimpleNamespace
import unittest
from medisaving.core import Store
from medisaving.ingest.commands import view


class ViewTests(unittest.TestCase):
    def test_bounded_source_order_and_exact_form(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory)
            rows = [{"offer_id": str(i), "source_group": "1058", "source_form_group": "3",
                     "strength": "0.25mg", "form": form, "unit_price_cents": price}
                    for i, (form, price) in enumerate([
                        ("tableta sublingual", 300), ("tableta de desintegración oral", 100),
                        ("tableta sublingual", 200), ("tableta sublingual", 250)])]
            dataset_id = store.put({"kind": "offers", "schema_version": 1, "offers": rows,
                "source": {"complete": True, "fetched_at": "2026-09-12", "warnings": ["verify_offer_forms"]}})
            args = SimpleNamespace(dataset_id=dataset_id, product="1058:3:0.25mg", form="Tableta Sublingual", offset=0, limit=2)
            result = view(args, store)
            self.assertEqual([r["offer_id"] for r in result["offers"]], ["0", "2"])
            self.assertEqual(result["next"], 2)
            self.assertEqual(result["order"], "source")
            args.offset = result["next"]
            self.assertEqual([r["offer_id"] for r in view(args, store)["offers"]], ["3"])
            self.assertIsNone(view(args, store)["next"])
            args.limit = 1000
            with self.assertRaises(ValueError):
                view(args, store)
