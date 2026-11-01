"""Deterministic detectors: language, escalation (P-01), allergies + ambiguity (P-02), simple fallbacks.
These run without the LLM, so safety routing still works if the API is down."""
import re

from .policy import AMBIGUOUS_ALLERGY_TERMS, CUSTOMER_ALLERGEN_MAP, mentions

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
HINGLISH_WORDS = {
    "hai", "hain", "chahiye", "mujhe", "kuch", "bhai", "log", "mein", "ke", "ka", "ki", "khaana", "khana",
    "nahi", "nahin", "aur", "ho", "raha", "rahi", "kya", "kar", "karo", "do", "dena", "wala", "wali", "accha",
    "acha", "thoda", "jaldi", "yaar", "hum", "hamare", "mere", "mera", "meri", "gale", "baad", "se", "bhi",
    "batao", "khane", "abhi", "liye", "zyada", "kam", "teekha", "tikha", "sab", "koi",
}


def detect_language(text: str) -> str:
    if DEVANAGARI.search(text or ""):
        return "hi"
    words = re.findall(r"[a-z]+", (text or "").lower())
    hits = sum(1 for w in words if w in HINGLISH_WORDS)
    return "hinglish" if hits >= 2 or (words and hits / len(words) >= 0.25) else "en"


# P-01: reaction / food safety / payment. Deliberately broad: a false escalation is cheap, a miss is not.
ESCALATION_PATTERNS = [
    # physical reaction after eating
    r"allergic reaction", r"\breaction\b", r"\bswell(ing|ed)?\b", r"\bswollen\b", r"\bitch(y|ing)?\b",
    r"\brash(es)?\b", r"\bhives\b", r"breath(ing|e)?\b", r"can'?t breathe", r"\bvomit", r"threw up",
    r"throwing up", r"\bnause", r"stomach ?(pain|ache|upset)", r"food poisoning", r"\bunwell\b",
    r"\b(feel|feeling|fell|got|felt) (sick|ill)\b", r"\bdiarr", r"\bkhujli\b", r"\bsujan\b", r"\bulti\b",
    r"pet (mein |me )?dard", r"\bsaans\b", r"tabiyat|tabiyet|tabeeyat",
    # food safety
    r"\bhair\b", r"\bplastic\b", r"(piece|bits?|shard)s? of glass", r"broken glass", r"glass (piece|in)",
    r"\binsect", r"cockroach", r"\bworms?\b", r"\bfly in\b", r"\bkeeda\b", r"\bbaal\b",
    r"\bspoil(ed|t)\b", r"\brotten\b", r"\bstale\b", r"\bexpired\b", r"bad smell", r"smell(s|ed|ing)? (bad|off|weird)",
    r"\bsmelly\b", r"\bstinks?\b", r"undercooked", r"under-cooked", r"\braw (chicken|meat|mutton|fish)",
    r"not (properly |fully )?cooked", r"\bfoul\b", r"\bmould|\bmold(y)?\b", r"\bbadboo\b",
    # payment
    r"charged (twice|two times|double|extra|more)", r"double[- ]charged", r"\bovercharg", r"wrong amount",
    r"\brefund", r"deducted (twice|two times|double)", r"money (was )?deducted", r"paise? kat",
    r"payment (issue|problem|failed|fail)", r"\bcharged\b.*\b(twice|again)\b",
    # Devanagari
    # 14:25 additions: paraphrases the first list missed (found via adv-03 and a phrasing probe)
    r"\b(gone|went) off\b", r"tast(ed|es|ing) (sour|off|weird|funny|bad|strange|rotten)", r"\boff taste\b",
    r"\bpuff(ed|y|ing)? up\b", r"\blips? (are |is |got |went )?(swell|swollen|puff|tingl|numb)", r"\btingl",
    r"\banaphyla", r"\bepi-?pen\b", r"allergy attack", r"\b(fell|got|feeling|felt|am|is) ill\b",
    r"\bloose motions?\b", r"\bdiarrh?oea|\bdiarrhea", r"\bdast\b", r"\bchakkar\b", r"ji (mich|ghabra)",
    r"\bhalf[- ]cooked\b", r"\bkacc?ha (tha|hai|chicken|mutton)", r"pink (inside|in the middle|chicken)",
    r"\bfungus\b", r"\bmaggots?\b", r"\b(stone|nail|thread|metal|wire|staple)s? (in|inside)\b",
    r"\b(paid|debited|deducted) (twice|two times|double)\b", r"(money|amount|payment) (got |was )?(debited|deducted)",
    r"\bnot (been )?refunded\b", r"\bchargeback\b", r"pais[ae] (wapas|vapas|kat)", r"\bextra (paise|paisa|money) (kat|liya|charged)",
    r"गला", r"खराब हो", r"जी मिचल", r"दस्त", r"पेट खराब", r"चक्कर", r"कच्चा", r"पैसे वापस",
    r"सूजन", r"खुजली", r"सांस", r"साँस", r"उल्टी", r"पेट (में )?दर्द", r"तबीयत", r"बाल", r"कीड़", r"प्लास्टिक",
    r"बासी", r"सड़", r"बदबू", r"रिफंड", r"दो बार", r"पैसे कट", r"ज़्यादा पैसे", r"ज्यादा पैसे",
]
ESCALATION_RE = re.compile("|".join(ESCALATION_PATTERNS), re.IGNORECASE)


def detect_escalation(text: str) -> str | None:
    m = ESCALATION_RE.search(text or "")
    return m.group(0) if m else None


ALLERGY_CONTEXT = re.compile(r"allerg|एलर्जी|intoleran|can'?t (eat|have)|cannot (eat|have)", re.IGNORECASE)
NO_ALLERGY = re.compile(r"\bno (food )?allerg|not allergic|koi allergy nahi|allergy nahi|कोई एलर्जी नहीं|"
                        r"no known allerg|don'?t have (any )?allerg", re.IGNORECASE)


OK_WORDS = re.compile(r"\b(fine|ok|okay|chalega|no problem|allowed)\b", re.IGNORECASE)


def _clauses(text: str) -> list[str]:
    return [c for c in re.split(r"[.!?;,\n।]|\bbut\b|\blekin\b", text or "", flags=re.IGNORECASE) if c.strip()]


def map_allergens(text: str) -> set[str]:
    found = set()
    for phrase, allergens in CUSTOMER_ALLERGEN_MAP.items():
        if DEVANAGARI.search(phrase):
            if phrase in text:
                found.update(allergens)
        elif mentions(text, phrase):
            found.update(allergens)
    return found


def allergy_state(user_turns: list[str], prev_assistant_asked: bool) -> tuple[set[str], bool]:
    """Scan user turns oldest->newest. Returns (allergens, still_ambiguous).
    Only clauses that talk about an allergy are mapped, so 'egg is fine' or 'fish curry please' never
    becomes an allergy. The reply to our own clarify question is read whole."""
    allergens, ambiguous = set(), False
    for i, turn in enumerate(user_turns):
        answering_clarify = prev_assistant_asked and i == len(user_turns) - 1
        for clause in _clauses(turn):
            if NO_ALLERGY.search(clause):
                continue
            if not (ALLERGY_CONTEXT.search(clause) or answering_clarify):
                continue
            if not ALLERGY_CONTEXT.search(clause) and OK_WORDS.search(clause):
                continue  # "egg is fine too" while answering is a diet statement, not an allergy
            mapped = map_allergens(clause)
            vague = any(mentions(clause, t) if not DEVANAGARI.search(t) else t in clause
                        for t in AMBIGUOUS_ALLERGY_TERMS)
            if mapped:
                allergens |= mapped
                ambiguous = vague and "tree_nut" not in mapped and "peanut" not in mapped
                if vague and ("peanut" in mapped) != ("tree_nut" in mapped):
                    # "peanuts and other nuts": the other nuts are still unresolved
                    ambiguous = bool(re.search(r"other nuts|all nuts|any nuts|nuts too", clause, re.I))
            elif ALLERGY_CONTEXT.search(clause) or vague:
                ambiguous = True
    return allergens, ambiguous


def fallback_diet(text: str) -> str | None:
    t = (text or "").lower()
    if re.search(r"\bjain\b|जैन", t):
        return "jain"
    if re.search(r"non[- ]?veg|मांसाहारी|नॉन[- ]?वेज", t):
        return "non-veg"
    if re.search(r"\begg(s)? (is |are )?(fine|ok|okay)|eggetarian|anda chalega", t):
        return "egg"
    if re.search(r"\bveg(etarian|gie)?\b|shakahari|शाकाहारी", t):
        return "veg"
    return None


def fallback_spice(text: str) -> str | None:
    t = (text or "").lower()
    if re.search(r"\bmild|not spicy|less spicy|kam (teekha|tikha|spicy)|कम तीखा", t):
        return "mild"
    if re.search(r"\bmedium\b", t):
        return "medium"
    if re.search(r"spicy|teekha|tikha|hot\b|तीखा", t):
        return "hot"
    return None


def fallback_numbers(text: str) -> dict:
    t = (text or "").lower()
    out = {}
    m = re.search(r"(?:under|below|budget(?: of| is)?|around|within|upto|up to|max|₹|rs\.?|inr)\s*(\d{2,5})", t)
    if m:
        out["budget_inr"] = int(m.group(1))
    m = re.search(r"(\d{1,3})\s*(?:min|mins|minute|minutes|मिनट)", t)
    if m:
        out["max_wait_min"] = int(m.group(1))
    m = re.search(r"(\d{1,2})\s*(?:people|persons|log|of us|guests|लोग)|for (\d{1,2})(?!\s*(?:min|rs|₹))", t)
    if m:
        out["party_size"] = int(m.group(1) or m.group(2))
    elif re.search(r"just me|only me|for myself|akela|sirf main", t):
        out["party_size"] = 1
    return out
