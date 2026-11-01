"""Hard rules P-03..P-08, applied in code before any ranking. Returns eligible ids and a rule trace."""
from schema import Profile, RuleTrace

from .policy import ALLERGEN_KEYWORDS, CUSTOMER_ALLERGEN_MAP, DIET_ALLOWED, JAIN_EXCLUDED, mentions


def hard_violations(item: dict, p: Profile) -> list[tuple[str, str]]:
    """List of (rule_id, detail) the item breaks for this profile. Empty list = eligible."""
    v = []
    for a in p.allergies:
        if a in item["allergens"]:
            v.append(("P-03", f"declared allergen {a}"))
        else:
            hit = next((k for k in ALLERGEN_KEYWORDS.get(a, []) if mentions(item["text"], k)), None)
            if hit:
                v.append(("P-03", f"text mentions '{hit}' ({a})"))
    if p.diet:
        if item.get("diet") not in DIET_ALLOWED[p.diet]:
            v.append(("P-04", f"diet {item.get('diet')} not allowed for {p.diet}"))
        elif p.diet == "jain":
            if item.get("jain_friendly") is not True:
                v.append(("P-04", "not jain_friendly"))
            hit = next((k for k in JAIN_EXCLUDED if mentions(item["text"], k)), None)
            if hit:
                v.append(("P-04", f"jain: text mentions '{hit}'"))
    if item.get("available") is not True:
        v.append(("P-05", "not available"))
    for ing in p.avoid_ingredients:
        ing = (ing or "").strip().lower()
        if ing and mentions(item["text"], ing):
            v.append(("P-06", f"mentions avoided '{ing}'"))
            continue
        # "no dairy" / "no nuts": a category word never appears in descriptions, so expand it with the
        # P-03 allergen data (declared allergens + keyword list) for that category.
        cats = CUSTOMER_ALLERGEN_MAP.get(ing.rstrip("s"), []) or (["peanut", "tree_nut"] if ing in ("nut", "nuts") else [])
        for a in cats:
            if a in item["allergens"] or any(mentions(item["text"], k) for k in ALLERGEN_KEYWORDS[a]):
                v.append(("P-06", f"avoided '{ing}' expands to {a}"))
                break
    if p.max_wait_min is not None and (item["prep_time_min"] is None or item["prep_time_min"] > p.max_wait_min):
        v.append(("P-07", f"prep {item['prep_time_min']} > {p.max_wait_min}"))
    if p.budget_inr is not None and (item["price_inr"] is None or item["price_inr"] > p.budget_inr):
        v.append(("P-08", f"price {item['price_inr']} > budget {p.budget_inr}"))
    return v


def apply_hard_rules(menu: dict, p: Profile) -> tuple[list[str], list[RuleTrace]]:
    eligible, trace = [], []
    for iid, item in menu.items():
        viol = hard_violations(item, p)
        for rule, detail in viol:
            trace.append(RuleTrace(rule_id=rule, item_id=iid, outcome="exclude", detail=detail))
        if not viol:
            eligible.append(iid)
    return eligible, trace
