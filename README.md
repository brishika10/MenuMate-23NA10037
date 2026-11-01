# MenuMate — Rishika Bhimrajka, 23NA10037

## Setup

Run these inside the project folder. Windows: use PowerShell.

| Step | Mac / Linux | Windows (PowerShell) |
|---|---|---|
| Create environment | `python3 -m venv ~/venvs/menumate` | `python -m venv $HOME\venvs\menumate` |
| Activate it | `source ~/venvs/menumate/bin/activate` | `$HOME\venvs\menumate\Scripts\Activate.ps1` |
| Install packages | `pip install -r requirements.txt` | `pip install -r requirements.txt` |
| Create .env | `cp .env.example .env` | `copy .env.example .env` |

If PowerShell blocks activation: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again.

Then fill in `LLM_API_KEY` and `LLM_MODEL` in `.env`.

## Run

```
python run.py --in kit/conversations_public.jsonl --out results/public_results.jsonl
```

## Model used

`gpt-4o-mini` (OpenAI, `LLM_BASE_URL=https://api.openai.com/v1`). Any OpenAI-compatible provider works by changing the three env vars; the code uses only chat completions with `response_format={"type": "json_object"}`.

## Notes for the reviewer

- Evaluate: `python eval.py` (public set) and `python eval.py --gold tests/adversarial.jsonl --results results/adversarial_results.jsonl`.
- Repeated-run experiment: `python tests/repeat_runs.py 5`.
- Layout: `src/detect.py` (escalation/allergy/language, code), `src/extract.py` (LLM profile + code union), `src/filters.py` (hard rules P-03..P-08), `src/rank.py` (scoring + soft penalties), `src/reply.py` (grounded reply + validator + templates), `src/pipeline.py` (`respond()`).
- Up to 2 LLM calls per turn (extract, reply); escalation detected by regex needs none. Rate limits/timeouts: 3 attempts with exponential backoff; auth/bad-request errors fail fast. If the LLM is unavailable, a code fallback still produces a safe output; run.py also catches any per-conversation crash.
- Known limitations: see SELF_AUDIT.md. No frontend (not required; dropped for time).

## Optional demo UI

`streamlit run streamlit_app.py` opens a chat UI that calls the same `respond()` as run.py, with dish cards (diet mark, price, spice, prep time, serves, allergens, the reason and its cited fields) and a "Why these?" panel showing the profile and rule trace. Menu text is HTML-escaped before rendering. Headless multi-turn UI test: `python tests/ui_smoke.py`.
