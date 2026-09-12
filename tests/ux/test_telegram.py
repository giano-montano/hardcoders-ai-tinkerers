import tempfile
from types import SimpleNamespace
import unittest
from medisaving.core import Store
from medisaving.analytics import rank
from medisaving.ux import telegram
from tests.helpers import fixture


class TelegramTests(unittest.TestCase):
    def test_labels_unknown_unit_and_partial_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            args = SimpleNamespace(dataset_id=store.put(fixture()), district=None, top=10, basis="pack")
            ranked = rank(args, store)
            result = telegram(SimpleNamespace(**ranked), store)
            text = "\n".join(result["messages"])
            self.assertIn("Unit: S/ 1.80 | Pack: S/ 54.00 (30 units)", text)
            self.assertIn("Unit: not reported | Pack: S/ 60.00", text)
            self.assertIn("Partial results", text)
            self.assertIsNone(result["parse_mode"])
