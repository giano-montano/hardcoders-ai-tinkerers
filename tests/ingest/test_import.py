import unittest
from medisaving.core import validate_dataset
from tests.helpers import fixture


class ImportTests(unittest.TestCase):
    def test_invalid_money_and_duplicate_ids(self):
        for invalid in (-1, 1.2, True, "1.20"):
            data = fixture()
            data["offers"][0]["unit_price_cents"] = invalid
            with self.assertRaises(ValueError):
                validate_dataset(data)
        data = fixture()
        data["offers"].append(data["offers"][0])
        with self.assertRaises(ValueError):
            validate_dataset(data)

    def test_coverage_is_required(self):
        data = fixture()
        del data["source"]["complete"]
        with self.assertRaises(ValueError):
            validate_dataset(data)
