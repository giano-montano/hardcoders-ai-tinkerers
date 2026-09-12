from copy import deepcopy
import unittest

from medisaving.ingest.normalize import canonical_offer, canonical_import
from medisaving.ingest.identity import ESCITALOPRAM_RULE
from tests.helpers import fixture


class IdentityTests(unittest.TestCase):
    def row(self, **changes):
        row = deepcopy(fixture()["offers"][0])
        row.update(medicine_key="ESCITALOPRAM OXALATO", strength="20 mg",
                   form="Tableta Recubierta", source_group="1515", source_form_group="3")
        row.update(changes)
        return row

    def test_verified_identity_preserves_prices_form_and_source(self):
        for form in ("Tableta Recubierta", "Comprimido Recubierto"):
            row = self.row(form=form)
            result = canonical_offer(row)
            self.assertEqual(result["medicine_key"], "escitalopram")
            self.assertEqual(result["identity_rule"], ESCITALOPRAM_RULE)
            self.assertEqual(result["source_values"]["substance"], "ESCITALOPRAM OXALATO")
            self.assertEqual(result["form"], form.lower())
            self.assertEqual(canonical_offer(result), result)
            for field in ("unit_price_cents", "pack_price_cents", "pack_units"):
                self.assertEqual(result[field], row[field])

    def test_unverified_identities_are_not_mapped(self):
        for changes in ({"source_group": "99"}, {"source_form_group": "4"},
                        {"strength": "25.5mg"}, {"strength": "10mg"},
                        {"form": "Tableta sublingual"}, {"form": "Solución"},
                        {"medicine_key": "escitalopram oxalato + otro"},
                        {"medicine_key": "otra sal"}, {"medicine_key": "digemid:1515"}):
            with self.subTest(changes=changes):
                self.assertNotIn("identity_rule", canonical_offer(self.row(**changes)))

    def test_import_migration_is_explicit_and_idempotent(self):
        dataset = fixture()
        dataset["offers"] = [self.row()]
        migrated = canonical_import(dataset)
        self.assertEqual(migrated["source"]["identity_profile"], "opm-identity-v1")
        self.assertEqual(migrated, canonical_import(migrated))
        self.assertEqual(dataset["offers"][0]["medicine_key"], "ESCITALOPRAM OXALATO")

    def test_stale_or_future_evidence_is_rejected(self):
        mapped = canonical_offer(self.row())
        for changes in ({"strength": "10mg"}, {"identity_rule": "future"},
                        {"medicine_key": "other"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                canonical_offer({**mapped, **changes})
        dataset = fixture()
        dataset["source"]["identity_profile"] = "future"
        with self.assertRaises(ValueError):
            canonical_import(dataset)
