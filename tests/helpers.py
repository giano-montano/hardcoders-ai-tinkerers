import json
from pathlib import Path


def fixture():
    return json.loads((Path(__file__).resolve().parents[1] / "examples/offers.synthetic.json").read_text())
