"""Run behaviours that depend on the LLM N times and print the raw outcome of every run."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()
from src.pipeline import respond  # noqa: E402

CASES = {
    "escalate-by-LLM-only": "The dal you sent tasted sour and I think it had gone off. Anyway, what else do you have?",
    "vague-allergy": "my son reacts badly to some nuts, what dessert can he have?",
}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
for name, msg in CASES.items():
    for i in range(N):
        o = respond(f"rep-{name}-{i}", [], msg)
        print(json.dumps({"case": name, "run": i + 1, "route": o.route, "allergies": o.profile.allergies,
                          "recs": [r.item_id for r in o.recommendations],
                          "p01": next((t.detail for t in o.rule_trace if t.rule_id == "P-01"), None)},
                         ensure_ascii=False))
