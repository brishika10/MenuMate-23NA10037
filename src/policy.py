"""Policy constants transcribed from kit/policy.md. The escalation texts are read from policy.md at import
so they are word-for-word, never retyped."""
import re
from pathlib import Path

POLICY_PATH = Path(__file__).resolve().parent.parent / "kit" / "policy.md"

# P-03 allergen keywords (name/description check)
ALLERGEN_KEYWORDS = {
    "peanut": ["peanut", "groundnut", "moongphali"],
    "tree_nut": ["cashew", "kaju", "almond", "badam", "pistachio", "pista", "walnut", "akhrot", "hazelnut"],
    "dairy": ["milk", "cream", "butter", "buttermilk", "ghee", "paneer", "cheese", "curd", "yogurt", "dahi",
              "khoya", "chenna", "malai"],
    "gluten": ["wheat", "maida", "atta", "semolina", "sooji", "rava", "noodle", "pasta", "penne", "pav", "brownie"],
    "egg": ["egg", "omelette", "mayonnaise", "mayo"],
    "soy": ["soy", "soya", "tofu"],
    "sesame": ["sesame", "til"],
    "shellfish": ["prawn", "shrimp", "crab", "lobster"],
    "fish": ["fish"],
    "mustard": ["mustard", "sarson", "kasundi"],
}

# Customer phrase -> allergens (policy "Allergen vocabulary" table, plus Devanagari equivalents)
CUSTOMER_ALLERGEN_MAP = {
    "peanut": ["peanut"], "groundnut": ["peanut"], "moongphali": ["peanut"],
    "cashew": ["tree_nut"], "almond": ["tree_nut"], "pistachio": ["tree_nut"], "walnut": ["tree_nut"],
    "kaju": ["tree_nut"], "badam": ["tree_nut"], "tree nut": ["tree_nut"], "tree_nut": ["tree_nut"],
    "milk": ["dairy"], "lactose": ["dairy"], "dairy": ["dairy"], "doodh": ["dairy"],
    "gluten": ["gluten"], "wheat": ["gluten"], "celiac": ["gluten"], "coeliac": ["gluten"],
    "seafood": ["fish", "shellfish"], "shellfish": ["shellfish"],
    "prawn": ["shellfish"], "shrimp": ["shellfish"], "crab": ["shellfish"],
    "fish": ["fish"], "til": ["sesame"], "sesame": ["sesame"], "soya": ["soy"], "soy": ["soy"],
    "egg": ["egg"], "mustard": ["mustard"],
    # Devanagari
    "मूंगफली": ["peanut"], "काजू": ["tree_nut"], "बादाम": ["tree_nut"], "दूध": ["dairy"],
    "गेहूं": ["gluten"], "अंडा": ["egg"], "अंडे": ["egg"], "तिल": ["sesame"], "मछली": ["fish"],
    "सरसों": ["mustard"],
}
# Allergy words that cannot be mapped with certainty -> P-02 clarify
AMBIGUOUS_ALLERGY_TERMS = ["nut", "dry fruit", "mewa", "मेवा", "nuts"]

# P-04 Jain exclusion words
JAIN_EXCLUDED = ["onion", "pyaz", "pyaaz", "garlic", "lahsun", "potato", "aloo", "carrot", "gajar", "beetroot",
                 "radish", "mooli", "ginger", "adrak"]

DIET_ALLOWED = {"veg": {"veg"}, "egg": {"veg", "egg"}, "non-veg": {"veg", "egg", "non-veg"}, "jain": {"veg"}}


def keyword_regex(word: str) -> re.Pattern:
    """Whole-word, case-insensitive, plural (s/es) allowed: 'cashews' matches, 'creamy' does not match 'cream'."""
    return re.compile(r"(?<![A-Za-z])" + re.escape(word) + r"(?:s|es)?(?![A-Za-z])", re.IGNORECASE)


def mentions(text: str, word: str) -> bool:
    return bool(keyword_regex(word).search(text or ""))


def _load_escalation_texts() -> dict:
    text = POLICY_PATH.read_text(encoding="utf-8")
    quotes = re.findall(r"^> (.+)$", text, flags=re.MULTILINE)
    en = next(q for q in quotes if q.startswith("I'm sorry"))
    hi = next(q for q in quotes if re.search(r"[ऀ-ॿ]", q))
    return {"en": en.strip(), "hi": hi.strip()}


ESCALATION_TEXT = _load_escalation_texts()
