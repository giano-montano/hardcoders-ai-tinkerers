import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from medisaving.core import Store


class PipelineTests(unittest.TestCase):
    def test_cli_pipeline_and_invalid_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            def run(*args):
                process = subprocess.run([sys.executable, "-m", "medisaving", "--data-dir", tmp, *args],
                                         capture_output=True, text=True)
                self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
                return json.loads(process.stdout)["data"]
            imported = run("ingest", "import", "examples/offers.synthetic.json")
            self.assertNotIn("offers", imported)
            ranked = run("analytics", "rank", imported["dataset_id"], "--district", "San Isidro", "--top", "2")
            self.assertEqual(ranked["selected"], 2)
            rendered = run("ux", "telegram", ranked["result_id"])
            self.assertEqual(len(rendered["messages"]), 3)
            self.assertTrue(Path(tmp, rendered["presentation_id"] + ".json").exists())
            with self.assertRaises(ValueError):
                Store(tmp).get("../../.env", "offers")

    def test_missing_artifact_returns_json_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = subprocess.run([sys.executable, "-m", "medisaving", "--data-dir", tmp,
                                      "analytics", "rank", "0" * 32], capture_output=True, text=True)
            self.assertEqual(process.returncode, 2)
            self.assertFalse(json.loads(process.stdout)["ok"])
