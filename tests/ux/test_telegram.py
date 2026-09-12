from types import SimpleNamespace
import unittest

from medisaving.ux import (STATUS_MESSAGES, TELEGRAM_SAFE_UTF16, google_maps_url,
                           offer_detail_text, offer_summary_text, prescription_notice,
                           render_status, split_telegram, telegram)
from tests.helpers import fixture


class MemoryStore:
    """UX tests do not exercise the filesystem-owned artifact store."""
    def __init__(self, ranking):
        self.ranking = ranking
        self.saved = []

    def get(self, artifact_id, kind):
        self.last_get = (artifact_id, kind)
        return self.ranking

    def put(self, artifact):
        self.saved.append(artifact)
        return "f" * 32


class TelegramTests(unittest.TestCase):
    def ranking(self, data):
        # Ranking is an input contract here, not behavior owned by the UX team.
        return {"kind": "ranking", "schema_version": 1, "source": data["source"],
                "groups": [{"medicine_key": "escitalopram", "strength": "20 mg", "form": "tablet",
                            "pack_units": 30,
                            "offers": [data["offers"][1], data["offers"][3], data["offers"][2]]}]}

    def test_labels_unknown_unit_partial_source_and_compact_options(self):
        store = MemoryStore(self.ranking(fixture()))
        result = telegram(SimpleNamespace(result_id="a" * 32, expand=False), store)
        text = "\n".join(result["messages"])
        self.assertIn("💰 S/ 54.00 per box · S/ 1.80 each", text)
        self.assertIn("💰 S/ 60.00 per box", text)
        self.assertIn("may not include every pharmacy", text)
        self.assertIn("✨ I found 1 more option", text)
        self.assertIsNone(result["parse_mode"])
        self.assertGreater(result["metrics"]["output_utf8_bytes"], 1)

    def test_summary_exposes_map_and_detail_actions(self):
        store = MemoryStore(self.ranking(fixture()))
        result = telegram(SimpleNamespace(result_id="a" * 32, expand=False), store)
        buttons = result["keyboards"][0]["inline_keyboard"]
        self.assertEqual(buttons[0][0]["text"], "🗺️ Open map")
        self.assertIn("google.com/maps/search/?api=1", buttons[0][0]["url"])
        self.assertEqual(buttons[-1][0]["callback_data"], "ux:details:o0")
        self.assertIn("ℹ️ OPTION 1 — DETAILS", result["interaction_responses"]["ux:details:o0"]["messages"][0])
        self.assertIn("ux:expand", result["interaction_responses"])

    def test_quantity_alert_is_only_based_on_verified_structured_data(self):
        data = self.ranking(fixture())
        row = data["groups"][0]["offers"][0]
        data["prescription_checks"] = [{
            "medicine_key": "escitalopram", "prescribed_units": 45,
            "quantity_confidence": "high", "partial_dispensing_available": True,
        }]
        result = telegram(SimpleNamespace(result_id="a" * 32, expand=False), MemoryStore(data))
        self.assertIn("appears to need 45 units", "\n".join(result["messages"]))
        self.assertIn("permitted partial dispensing", "\n".join(result["messages"]))
        self.assertIn("Do not change the prescribed dose", "\n".join(result["messages"]))
        low_confidence = prescription_notice(row, {"prescribed_units": 45, "quantity_confidence": "low"})
        self.assertIn("could not confirm", low_confidence)
        self.assertNotIn("another box", low_confidence)

    def test_map_needs_a_branch_address_not_the_user_location(self):
        row = self.ranking(fixture())["groups"][0]["offers"][0]
        self.assertIn("SYNTHETIC+ADDRESS+2", google_maps_url(row))
        row["address"] = None
        self.assertIsNone(google_maps_url(row))

    def test_cards_use_visual_hierarchy_without_missing_data_noise(self):
        row = self.ranking(fixture())["groups"][0]["offers"][0]
        summary = offer_summary_text(row, 1)
        details = offer_detail_text(row, 1)
        self.assertTrue(summary.startswith("💊 OPTION 1"))
        self.assertIn("🏪", summary)
        self.assertIn("📍", summary)
        self.assertIn("💰", summary)
        self.assertIn("📦", details)
        self.assertNotIn("not reported", summary)

    def test_expand_includes_remaining_ranked_options(self):
        store = MemoryStore(self.ranking(fixture()))
        compact = telegram(SimpleNamespace(result_id="a" * 32, expand=False), store)
        expanded = telegram(SimpleNamespace(result_id="a" * 32, expand=True), store)
        self.assertLess(len(compact["messages"]), len(expanded["messages"]))
        self.assertNotIn("more comparable option", "\n".join(expanded["messages"]))

    def test_empty_long_and_telegram_characters_are_safe(self):
        data = fixture()
        empty_ranking = {"kind": "ranking", "schema_version": 1, "source": data["source"], "groups": []}
        empty = telegram(SimpleNamespace(result_id="a" * 32, expand=False), MemoryStore(empty_ranking))
        self.assertIn(STATUS_MESSAGES["no_results"], empty["messages"][0])
        chunks = split_telegram("📍_" * 4000)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(item.encode("utf-16-le")) // 2 <= TELEGRAM_SAFE_UTF16 for item in chunks))

    def test_explicit_statuses_do_not_invent_context(self):
        for state, expected in STATUS_MESSAGES.items():
            rendered = render_status(SimpleNamespace(state=state), MemoryStore({}))
            self.assertEqual(rendered["messages"], [expected])
            self.assertIsNone(rendered["parse_mode"])
            self.assertTrue(expected[0] in "📷📍🔎😕⚠️✨")
