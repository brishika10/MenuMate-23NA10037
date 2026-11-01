# DECISIONS — running log

Format: `[HH:MM] decision — why (and anything tried/dropped)`

- [setup] Created venv at `$HOME\venvs\menumate` (Python 3.12.3), outside the project so it never lands in the zip.
- [setup] Pre-installed `openai`, `pydantic`, `python-dotenv` while waiting for the starter kit; will reconcile with the kit's `requirements.txt`.
- [setup] Kit arrived nested in `menumate_candidate_kit/menumate-starter/`; flattened into project root so `run.py` is top-level. Installed kit `requirements.txt` (matches what was pre-installed). Check run stops with `NotImplementedError` as expected.
- [setup] Provider: OpenAI (via the `openai` SDK, `LLM_BASE_URL=https://api.openai.com/v1`) instead of Groq. Code still reads only `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL` and avoids OpenAI-only features beyond JSON mode, so reviewers can swap in Groq or another OpenAI-compatible provider.
- [13:15] Research: no open-source repo combines deterministic allergen filtering + escalation guardrail + grounded recs (closest: Rasa/LangChain food bots). Writing our own code — the brief forbids importing earlier code, and copied code is a similarity risk.
- [13:15] Policy P-02 means the only question we may ask is about an ambiguous allergy. So this is a single-decision pipeline per turn, not open-ended slot filling: escalate? → clarify? → profile → hard filter → rank → reply.
- [13:15] Rejected multi-agent: adds latency (p95 target is under 4 s), rate-limit pressure and audit difficulty, for no gain. Using 2 LLM calls max (extract, reply); escalate/clarify skip the reply call.
- [13:15] Rejected RAG/embeddings: 60 dishes fit in context; hard filter + transparent scoring function is cheaper and auditable. Only the filtered top candidates go to the reply LLM, wrapped as data.
- [13:15] Menu kept as-is (not edited); normalized in code at load: tokens, declared + keyword-derived allergens, Jain-violation flag. Policy tables become Python constants; escalation text copied verbatim.
- [13:29] Iteration-1 plan (deadline 15:00, only ~90 min left, so the 10-min buffer is non-negotiable):
  - Phase A 13:30–13:55: `src/policy.py` (constants), `src/menu.py` (load + normalize), `src/filters.py` (P-03..P-08 with trace), `src/detect.py` (escalation + ambiguous-allergy + language, regex in EN/HI/Hinglish). run.py try/except per conversation.
  - Phase B 13:55–14:15: `src/llm.py` (env-only client, JSON mode, backoff), `src/extract.py` (LLM profile + code union on safety fields, validate, retry once, code fallback), `src/rank.py` (relevance + separate soft penalties, course-diverse set).
  - Phase C 14:15–14:30: `src/reply.py` (grounded reply, validator, regenerate once, template fallback); wire `pipeline.respond`. Run public set.
  - Phase D 14:30–14:45: `eval.py` (independent hard-rule checker re-implemented from policy.md, route/field accuracy, latency, tokens), `tests/adversarial.jsonl`, 5x repeat run; EVAL.md, SELF_AUDIT.md, README model name.
  - Phase E 14:45–14:50: zip (move .env out first), check size, upload by 14:50.
  - Frontend (Streamlit) DROPPED for iteration 1: it isn't graded and there's no time. Kept the design notes in case time is left.
