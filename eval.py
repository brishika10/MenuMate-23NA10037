"""Independent evaluator. Re-implements the hard-rule checks from policy.md WITHOUT importing src/ (so a bug in
our filter is not hidden by calling it again), and scores routes/fields against the gold labels.

    python eval.py --gold kit/conversations_public.jsonl --results results/public_results.jsonl
"""
import argparse
import json
import re
import statistics

FIELDS = ["diet", "allergies", "party_size", "budget_inr", "max_wait_min", "spice_tolerance", "language"]
KW = {"peanut": "peanut groundnut moongphali", "tree_nut": "cashew kaju almond badam pistachio pista walnut akhrot hazelnut",
      "dairy": "milk cream butter buttermilk ghee paneer cheese curd yogurt dahi khoya chenna malai",
      "gluten": "wheat maida atta semolina sooji rava noodle pasta penne pav brownie", "egg": "egg omelette mayonnaise mayo",
      "soy": "soy soya tofu", "sesame": "sesame til", "shellfish": "prawn shrimp crab lobster", "fish": "fish",
      "mustard": "mustard sarson kasundi"}
JAIN = "onion pyaz pyaaz garlic lahsun potato aloo carrot gajar beetroot radish mooli ginger adrak".split()
ESC_EN = "I'm sorry this happened."
# Paid price for gpt-4o-mini (USD per 1M tokens) — update if LLM_MODEL changes.
PRICE_IN, PRICE_OUT = 0.15, 0.60


def has(text, w):
    return re.search(r"(?<![a-z])" + re.escape(w) + r"(es|s)?(?![a-z])", text.lower()) is not None


def price(v):
    m = re.search(r"\d+", str(v))
    return int(m.group()) if m else None


def violations(dish, prof):
    """Hard-rule check written from policy.md, independent of src/filters.py."""
    t = dish["name"] + " " + dish["description"]
    out = []
    if dish.get("available") is not True:
        out.append("P-05")
    for a in prof.get("allergies") or []:
        if a in dish["allergens"] or any(has(t, w) for w in KW[a].split()):
            out.append("P-03:" + a)
    d = prof.get("diet")
    ok = {"veg": ["veg"], "egg": ["veg", "egg"], "jain": ["veg"], "non-veg": ["veg", "egg", "non-veg"]}
    if d and dish["diet"] not in ok[d]:
        out.append("P-04")
    if d == "jain" and (dish["jain_friendly"] is not True or any(has(t, w) for w in JAIN)):
        out.append("P-04:jain")
    for ing in prof.get("avoid_ingredients") or []:
        if has(t, ing):
            out.append("P-06")
    if prof.get("max_wait_min") is not None and dish["prep_time_min"] > prof["max_wait_min"]:
        out.append("P-07")
    if prof.get("budget_inr") is not None and (price(dish["price_inr"]) or 10**9) > prof["budget_inr"]:
        out.append("P-08")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="kit/conversations_public.jsonl")
    ap.add_argument("--results", default="results/public_results.jsonl")
    ap.add_argument("--menu", default="kit/menu.json")
    a = ap.parse_args()
    menu = {d["id"]: d for d in json.load(open(a.menu, encoding="utf-8"))}
    gold = {c["conversation_id"]: c for c in map(json.loads, open(a.gold, encoding="utf-8")) if c.get("gold")}
    res = [json.loads(l) for l in open(a.results, encoding="utf-8") if l.strip()]

    viol, route_ok, field_hits, field_tot, lat, ptok, ctok = [], 0, {f: 0 for f in FIELDS}, {f: 0 for f in FIELDS}, [], [], []
    first_valid, replies = 0, 0
    for r in res:
        g = gold.get(r["conversation_id"], {}).get("gold")
        lat.append(r["latency_ms"]); ptok.append(r["tokens"]["prompt"]); ctok.append(r["tokens"]["completion"])
        for t in r["rule_trace"]:
            if t["rule_id"] == "VALIDATOR":
                replies += 1
                first_valid += t["outcome"] == "pass"
        ids = [x["item_id"] for x in r["recommendations"]]
        if r["route"] != "recommend" and ids:
            viol.append((r["conversation_id"], "recs on non-recommend route"))
        if r["route"] == "escalate" and not r["reply"].startswith(("I'm sorry this happened.", "हमें खेद है")):
            viol.append((r["conversation_id"], "escalation text not verbatim"))
        if not g:
            continue
        # check against the GOLD profile (+context) and the gold must_exclude list
        gp = dict(g["profile"]); gp.update(g.get("context") or {})
        for iid in ids:
            if iid not in menu:
                viol.append((r["conversation_id"], f"{iid} not on menu"))
                continue
            v = violations(menu[iid], gp)
            if v or iid in g["must_exclude"]:
                viol.append((r["conversation_id"], f"{iid} {v or 'in must_exclude'}"))
        route_ok += r["route"] == g["route"]
        for f in FIELDS:
            if f in g["profile"]:
                field_tot[f] += 1
                got, exp = r["profile"].get(f), g["profile"][f]
                if isinstance(exp, list):
                    got, exp = sorted(got or []), sorted(exp)
                field_hits[f] += got == exp

    n = len([r for r in res if r["conversation_id"] in gold])
    print(f"conversations: {len(res)} (with gold: {n})")
    print(f"HARD-RULE VIOLATIONS: {len(viol)}", viol)
    print(f"route accuracy: {route_ok}/{n}")
    for f in FIELDS:
        if field_tot[f]:
            print(f"  field {f}: {field_hits[f]}/{field_tot[f]}")
    print(f"groundedness (first-attempt validator pass): {first_valid}/{replies}")
    lat_s = sorted(lat)
    p95 = lat_s[min(len(lat_s) - 1, int(round(0.95 * (len(lat_s) - 1))))]
    print(f"latency ms: median {statistics.median(lat)}, p95 {p95}, max {max(lat)}")
    ap_, ac_ = statistics.mean(ptok), statistics.mean(ctok)
    cost = (ap_ * PRICE_IN + ac_ * PRICE_OUT) / 1e6
    print(f"avg tokens/turn: prompt {ap_:.0f}, completion {ac_:.0f}; cost/turn ≈ ${cost:.6f} (@ ${PRICE_IN}/${PRICE_OUT} per 1M)")


if __name__ == "__main__":
    main()
