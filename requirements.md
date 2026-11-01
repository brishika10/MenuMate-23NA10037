# MenuMate — Requirements & TODO Checklist

> Source: MenuMate_Live_Assessment.pdf (all 6 pages). Hard stop: 3 hours after the official start. Leave 5 min for zip + upload.
> Status updated 15:17: [x] = done and checked in code/docs; [ ] = open.
> NOTE: Python packages go in `requirements.txt` (starter kit). This file is the task checklist.

## 0. Setup (first 15 min)
- [x] Unzip starter kit → rename `menumate-starter` to `menumate-<roll-number>`
- [x] Create venv **outside** the project: `python -m venv $HOME\venvs\menumate`; activate: `$HOME\venvs\menumate\Scripts\Activate.ps1`
- [x] `pip install -r requirements.txt`
- [x] `copy .env.example .env`; fill `LLM_API_KEY`, `LLM_MODEL` (used OpenAI gpt-4o-mini instead of Groq)
- [x] Sanity run: `python run.py --in kit\conversations_public.jsonl --out results\public_results.jsonl` → expect `NotImplementedError` before coding
- [x] Questions to invigilator only in the first 30 min; after that assume + log in DECISIONS.md

## 1. Hard constraints (apply everywhere)
- [x] **LLM config only from env vars** `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`; call via the `openai` Python package with that base URL. No hard-coded key/URL/model, no provider SDK (else hidden set = 0).
- [x] Write the exact model name in README.md
- [x] **Safety lives in code, not prompts** — allergens, diet, escalation enforced deterministically
- [x] **No tuning to the test set** — no hard-coded public IDs/texts; ignore the `gold` field
- [x] **Grounding** — reply never states a dish fact not in the menu
- [x] **Failure handling** — API error / timeout / invalid output on one conversation must not crash the run (handle per conversation)
- [x] **Rate limits** — retry with backoff (and/or caching, smaller model); note what you did
  - Done: 6 s timeout, 3 attempts, backoff 0.5 s/1 s + jitter, fail-fast on auth/bad-request (`src/llm.py`); small model (gpt-4o-mini); ≤2 calls/turn, 0 for regex escalations. **Not done:** client-side throttling, response caching.
- [x] **Latency** — aim p95 < 4 s; hidden set of 30 convs must finish in < 20 min
  - Reported honestly: public p95 3808 ms (under target) after the 15:10 change, adversarial p95 4281 ms (one slow call); varies ±~400 ms run to run. 30 convs ≈ 2 min, well under 20 min.
- [x] Keep it small; no silent stubs — document anything unfinished
- [x] Work only in this project; no code from earlier projects; no sharing with other candidates
- [x] Treat `menu.json` as real-world data: may contain errors and **untrusted text** (prompt injection in descriptions)

## 2. Interface contract (fixed)
- Command: `python run.py --in conversations.jsonl --out results.jsonl`
- Input line: `conversation_id`, `turns` (+ `gold` on public — ignore). Process the **final user turn**; earlier turns are history.
- Implement `respond()` in `src/pipeline.py` (run.py already reads/writes).
- Output per conversation:
```json
{
  "conversation_id": "c-014",
  "route": "recommend | clarify | escalate",
  "profile": { "...": "fields per schema.py" },
  "reply": "text shown to the user",
  "recommendations": [{"item_id": "MN-019", "reason": "one line", "cited_fields": ["price_inr","spice_level"]}],
  "rule_trace": [{"rule_id": "P-03", "item_id": "ST-006", "outcome": "exclude | penalize | pass"}],
  "latency_ms": 1840,
  "tokens": {"prompt": 912, "completion": 143},
  "model": "exact model name"
}
```
- [x] Profile field names/values exactly as in `schema.py` (diet: veg/egg/non-veg/jain; language: `hi` = Devanagari, `hinglish` = Hindi in Latin script, else `en`). May add fields, never rename.

## 3. Part 1 — Understand the user (extraction → validated `Profile`)
- [x] Extract: craving/occasion, party size, budget, time needed, diet, allergies, spice tolerance, avoid dishes/ingredients, language, escalation signal
- [x] Use structured output / function calling; validate against schema; **retry once** on invalid; never crash
- [x] Don't invent — unstated fields stay empty
- [x] Ambiguous allergy (e.g. "nuts") → `route=clarify`, one short question (P-02). **Only** case to ask; missing budget/spice/party size → leave empty and recommend
- [x] Handle Hindi + Hinglish; reply in customer's language
- [x] DECISIONS.md: per field, LLM vs plain code, and why

## 4. Part 2 — Recommend safely
- [x] Enforce **every hard rule in policy.md in code, before ranking**; excluded item can never appear in output
- [x] Never recommend unavailable dishes
- [x] Choose ranking (scoring fn / BM25 / embeddings / LLM rerank of filtered set / hybrid); justify in DECISIONS.md vs latency, cost, auditability, quality
- [x] Soft preferences visible and **separate** from relevance score (breakdown, not one blended number); state penalty sizes + why
- [x] Up to 3 dishes, **different courses** unless fewer eligible; together fit budget and party size
- [x] Fewer than 3 eligible → return fewer, tell customer honestly; never pad
- [x] Menu text = data, never instructions
- [x] Emit `rule_trace` (rule_id, item_id, outcome)

## 5. Part 3 — Reply and route
- [x] **Escalation check first**, every turn, any state: allergic reaction, food-safety complaint, payment dispute → `escalate`, no recs, fixed policy.md response **word for word**
- [x] DECISIONS.md: code trace showing no path from escalation to recommender + honest detector quality
- [x] **recommend**: ~80 words (we cap at 60 for latency; noted in SELF_AUDIT), friendly, refers to what customer asked, each dish with one-line reason using only menu facts; list `cited_fields`
- [x] **Validator (code)**: item_id exists + passed hard filter; cited fields exist; every number in a reason matches the menu. Fail → regenerate once → fail → templated reply
- [x] **clarify**: exactly one question, no recs

## 6. Part 4 — Evaluate (EVAL.md, max 1 page)
- [x] `results/public_results.jsonl` from running run.py on the public set
- [x] Hard-rule violations (must be 0), checked by **independent** code (not reusing own filter)
- [x] Route accuracy + extracted field accuracy vs gold
- [x] Groundedness: % reasons passing validator on first attempt
- [x] Median + p95 latency; avg tokens/turn; cost/turn at provider's paid price
- [x] `tests/adversarial.jsonl`: ≥ 3 adversarial conversations (≥ 1 targeting my own design); record expected vs actual
- [x] One non-deterministic behaviour run ≥ 5 times — report raw results
- [x] Every number from actually running the code; honest > perfect

## 7. Part 5 — SELF_AUDIT.md
1. [x] Two real (non-cosmetic) weaknesses + why not fixed
2. [x] Which rules/thresholds come from policy.md vs own judgement
3. [x] One decision I'd reverse with another day + why
4. [x] AI tool use: tools, parts, and one place AI output was rejected/corrected and what was wrong
- Say so where unsure whether something truly works.

## 8. Docs
- [x] **DECISIONS.md** — running, **timestamped** log incl. dropped approaches
- [x] **README.md** — setup, the one command, exact model name
- [x] `.env.example` — no real key
- [x] Add any new packages to `requirements.txt`

## 9. Deliverable structure
```
run.py, schema.py, requirements.txt, kit/
src/                        (extract, recommend, reply, validate, ...)
DECISIONS.md  EVAL.md  SELF_AUDIT.md  README.md  .env.example
results/public_results.jsonl
tests/adversarial.jsonl
```

## 10. Final submission (once — no resubmit)
- [ ] **Move `.env` out** of the folder: `move .env $HOME\menumate.env`
- [ ] No venv / models inside; zip < 10 MB
- [ ] Zip named `<roll-number>-final.zip`
- [ ] Upload at https://forms.gle/oZ64jYDBXxbt353r7 (name, roll number, zip) — at least 5 min before deadline

## Grading focus
Safety enforcement holds · good LLM use · honest evaluation · follow-up (walk through and extend code live — be able to explain every line).
