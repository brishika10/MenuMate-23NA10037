# SELF_AUDIT

## 1. Two real weaknesses (and why not fixed)
1. **Escalation recall relies on a keyword list + one LLM flag.** The route is watertight (escalation returns before
   extraction-dependent code and before the recommender), but the detector is not. Even after adding paraphrases at 14:23, "my daughter broke out in red spots after the korma" and "something hard
   and crunchy in the biryani" are not in my regex (checked); it escalates only if the LLM flags it. If the API is down, only the
   regex runs. Not fixed: a proper fix needs a labelled set of complaint phrasings (EN/HI/Hinglish) to measure recall,
   which I did not have time to build; I widened the list and made it over-fire instead.
2. **Ranking quality is shallow.** Relevance is token overlap between the LLM's `craving` phrase and dish text, plus
   course words and a diet bonus. "Thai-ish and spicy" (c-002) gets Penne Arrabbiata because the only Thai dish is
   excluded and nothing models cuisine similarity. Also, "fits budget and party size together" only checks the budget
   sum; it does not check that total servings cover the party. Not fixed: safety and grounding were the priority in
   3 hours, and an LLM rerank of the filtered set would add a third call and push p95 further past 4 s.

Also unsure: the LLM still invents an allergen on clarify turns (see EVAL repeated runs), and the Hinglish detector
is a word list (≥2 hits) — short Hinglish messages like "kuch meetha" could come out `en`.

## 2. Policy vs my judgement
From policy.md: order of checks; escalation categories and both fixed texts (parsed from the file); P-02 trigger;
allergen vocabulary + customer-phrase table; P-03 keyword list and whole-word/plural matching; P-04 diet table and
Jain word list; P-05..P-08 as written; P-09 spice bands (mild ≥2, medium =4, hot <2); P-10 party ≥3 → serves ≥2,
budget fit, course variety.
My judgement: penalty sizes (spice −2 per level above 1 for mild, capped −4; −2 otherwise; party −1), course prior
(main 0.5 … beverage 0.1), relevance weights (1.5/word, +2 course word, +1.5 diet match, +1 "light"), escalation
regex word list, Hinglish word list and the ≥2 threshold, "dry fruit / mewa" as ambiguous, failing closed on
unparseable price/prep time, stripping instruction-like text from descriptions before the LLM sees them, LLM
ambiguity counting only when code mapped no allergen, the run.py error fallback.

## 3. One decision I'd reverse with another day
Reading the extraction schema **only** from the LLM for diet/numbers. I'd extract the safety-relevant hard-filter
fields (diet, max_wait_min, budget) with code *and* the LLM and, when they disagree, take the stricter one — the same
union trick I already use for allergies. Today an LLM misread of "egg is fine" vs "no egg" changes the filter.

## 4. AI tool use
Tool: Claude Code (Claude Opus) in VS Code, used for: reading the brief and kit, planning, writing all modules,
the eval script, adversarial cases, and drafting these docs. I reviewed outputs and test runs and directed fixes.
Corrected/rejected AI output:
- The first allergy parser mapped "egg is fine too" (the answer to "any allergies?") to an **egg allergy** and the
  "no X" fallback produced `avoid_ingredients=["allergi"]` — caught on the first run, fixed with a "fine/ok" check.
- A frontend research sub-agent proposed 0–3 chilli icons (menu uses 0–4) and a "Nut-free" suggestion chip, which
  would violate the policy's "never promise nut-free" — rejected.
- A "relevance gate" that dropped zero-relevance picks was written and then removed: it reduced variety for no
  safety gain. A diet bonus I added boosted the injected DS-047 brownie for an egg customer; restricted it to
  main/starter/rice.
