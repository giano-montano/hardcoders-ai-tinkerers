from types import SimpleNamespace
import unittest

from medisaving.ux import STATUS_MESSAGES, TELEGRAM_SAFE_UTF16, render_status, split_telegram, telegram
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
        self.assertIn("Unit price: S/ 1.80 | Box price: S/ 54.00 | Units per box: 30", text)
        self.assertIn("Unit price: not reported | Box price: S/ 60.00", text)
        self.assertIn("Coverage is partial", text)
        self.assertIn("1 more comparable option is available", text)
        self.assertIsNone(result["parse_mode"])
        self.assertGreater(result["metrics"]["output_utf8_bytes"], 1)

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
