"""Load kit/menu.json once and normalize it. Menu text is untrusted data: it is only ever matched against
keyword lists or passed to the LLM inside a data block, never executed or obeyed."""
import json
import re
from pathlib import Path

MENU_PATH = Path(__file__).resolve().parent.parent / "kit" / "menu.json"
# Instruction-like text inside menu data (prompt injection). Cut from the description shown to the LLM;
# keyword rules still run on the full original text so nothing safety-relevant is lost.
INJECTION = re.compile(r"(note to (the )?(ai|assistant|model)|ignore (the |all |your |previous )|"
                       r"always recommend|system prompt|you must|as an ai).*$", re.IGNORECASE | re.DOTALL)
NUMERIC_FIELDS = ["price_inr", "serves", "prep_time_min", "spice_level"]


def _to_int(v):
    """Coerce '₹300' / '300' / 300.0 to int; None if unparseable (rules then fail closed)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        m = re.search(r"\d+", v.replace(",", ""))
        return int(m.group()) if m else None
    return None


def load_menu() -> dict:
    raw = json.loads(MENU_PATH.read_text(encoding="utf-8"))
    menu = {}
    for d in raw:
        if not isinstance(d, dict) or "id" not in d:
            continue
        item = dict(d)
        for f in NUMERIC_FIELDS:
            item[f] = _to_int(d.get(f))
        item["allergens"] = [a for a in (d.get("allergens") or []) if isinstance(a, str)]
        item["name"] = str(d.get("name") or "")
        item["description"] = str(d.get("description") or "")
        item["text"] = item["name"] + " " + item["description"]
        clean = INJECTION.sub("", item["description"]).strip()
        item["llm_description"] = clean
        item["injection_flag"] = clean != item["description"].strip()
        menu[item["id"]] = item
    return menu


MENU = load_menu()
