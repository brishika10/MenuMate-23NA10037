"""Ranking of the already-filtered set. Relevance and soft penalties are kept as separate numbers
(see DECISIONS.md for the sizes), then a course-diverse set of up to 3 is picked."""
import re

from schema import Profile, RuleTrace

# Penalty sizes (soft rules P-09, P-10). Relevance is roughly 0..4, so a penalty of 2 outweighs
# one matching word but not a strong match.
SPICE_PENALTY = 2.0        # P-09: mild & level>=2 (per level above 1, capped 2x), medium & level 4, hot & level<2
PARTY_PENALTY = 1.0        # P-10: party>=3 and serves<2
COURSE_PRIOR = {"main": 0.5, "starter": 0.3, "rice": 0.3, "dessert": 0.2, "bread": 0.1, "beverage": 0.1}

STOP = {"something", "some", "want", "for", "and", "the", "a", "an", "with", "food", "dish", "please", "kuch",
        "chahiye", "craving", "like", "ish", "i", "me", "to", "of", "good", "nice", "options", "option"}
COURSE_WORDS = {"starter": ["starter", "snack", "appetizer", "app"], "main": ["main", "curry", "dinner", "lunch", "meal"],
                "bread": ["bread", "naan", "roti", "paratha"], "rice": ["rice", "biryani", "pulao"],
                "dessert": ["dessert", "sweet", "meetha"], "beverage": ["drink", "beverage", "lassi", "cooler", "chai"]}
LIGHT = {"light", "halka", "हल्का"}


def _tokens(s: str) -> set[str]:
    return {w.rstrip("s") for w in re.findall(r"[a-z]+", (s or "").lower()) if w not in STOP and len(w) > 1}


def relevance(item: dict, p: Profile) -> float:
    want = _tokens(p.craving or "")
    score = 0.0
    have = _tokens(item["text"] + " " + str(item.get("cuisine", "")))
    score += 1.5 * len(want & have)
    for course, words in COURSE_WORDS.items():
        if want & {w.rstrip("s") for w in words} and item.get("course") == course:
            score += 2.0
    # A stated non-veg/egg diet is also a positive wish, not just a filter ("non-veg chahiye").
    if p.diet in ("non-veg", "egg") and item.get("diet") == p.diet and item.get("course") in {"main", "starter", "rice"}:
        score += 1.5
    if want & LIGHT and (item.get("spice_level") or 0) <= 1 and item.get("course") in {"main", "rice", "starter"}:
        score += 1.0
    return score


def soft_penalties(item: dict, p: Profile) -> dict:
    pen = {}
    lvl = item.get("spice_level")
    if lvl is not None and p.spice_tolerance:
        if p.spice_tolerance == "mild" and lvl >= 2:
            pen["P-09"] = -SPICE_PENALTY * min(2, lvl - 1)
        elif p.spice_tolerance == "medium" and lvl >= 4:
            pen["P-09"] = -SPICE_PENALTY
        elif p.spice_tolerance == "hot" and lvl < 2:
            pen["P-09"] = -SPICE_PENALTY
    if p.party_size and p.party_size >= 3 and (item.get("serves") or 0) < 2:
        pen["P-10"] = -PARTY_PENALTY
    return pen


def requested_dishes(menu: dict, message: str) -> list[str]:
    """Dish ids the customer names in the latest message ("order sweet lassi"). Whole name, case-insensitive,
    ignoring bracketed parts like "(2 pcs)" and a trailing plural."""
    msg = " " + re.sub(r"[^a-z0-9 ]+", " ", (message or "").lower()) + " "
    msg = re.sub(r"\s+", " ", msg)
    out = []
    for iid, it in menu.items():
        name = re.sub(r"\(.*?\)", "", it["name"].lower())
        name = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", name)).strip()
        if name and re.search(r" " + re.escape(name) + r"(s|es)? ", msg):
            out.append(iid)
    return out


def rank(menu: dict, eligible: list[str], p: Profile,
         requested: list[str] | None = None) -> tuple[list[dict], list[RuleTrace], dict]:
    scored = []
    for iid in eligible:
        it = menu[iid]
        rel = relevance(it, p)
        pen = soft_penalties(it, p)
        total = rel + sum(pen.values()) + COURSE_PRIOR.get(it.get("course"), 0)
        scored.append({"id": iid, "relevance": rel, "penalties": pen, "total": round(total, 2)})
    req = set(requested or [])
    # A dish the customer named and that passed the hard filter goes first, whatever its score.
    scored.sort(key=lambda s: (s["id"] not in req, -s["total"], s["id"]))

    # Greedy pick: different courses; keep the combined price within budget when one is stated (P-10).
    picked, courses, spent = [], set(), 0
    for s in scored:
        it = menu[s["id"]]
        if it.get("course") in courses and s["id"] not in req:
            continue
        if p.budget_inr is not None and spent + (it["price_inr"] or 0) > p.budget_inr:
            continue
        picked.append(s)
        courses.add(it.get("course"))
        spent += it["price_inr"] or 0
        if len(picked) == 3:
            break
    trace = []
    for s in picked:
        if s["penalties"]:
            for rule, val in s["penalties"].items():
                trace.append(RuleTrace(rule_id=rule, item_id=s["id"], outcome="penalize", detail=f"{val}"))
        trace.append(RuleTrace(rule_id="P-03..P-08", item_id=s["id"], outcome="pass",
                               detail=f"relevance={s['relevance']} total={s['total']}"))
    meta = {"requested_eligible": [s["id"] for s in picked if s["id"] in req],
            "requested_excluded": sorted(req - {s["id"] for s in picked}), "total_price": spent, "over_budget": bool(p.budget_inr is not None and spent > p.budget_inr),
            "scores": {s["id"]: {k: s[k] for k in ("relevance", "penalties", "total")} for s in scored[:8]}}
    return picked, trace, meta
