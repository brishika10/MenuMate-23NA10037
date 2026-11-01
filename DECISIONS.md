# DECISIONS — running log

Format: `[HH:MM] decision — why (and anything tried/dropped)`

- [setup] Created venv at `$HOME\venvs\menumate` (Python 3.12.3), outside the project so it never lands in the zip.
- [setup] Pre-installed `openai`, `pydantic`, `python-dotenv` while waiting for the starter kit; will reconcile with the kit's `requirements.txt`.
- [setup] Kit arrived nested in `menumate_candidate_kit/menumate-starter/`; flattened into project root so `run.py` is top-level. Installed kit `requirements.txt` (matches what was pre-installed). Check run stops with `NotImplementedError` as expected.
- [setup] Provider: OpenAI (via the `openai` SDK, `LLM_BASE_URL=https://api.openai.com/v1`) instead of Groq. Code still reads only `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL` and avoids OpenAI-only features beyond JSON mode, so reviewers can swap in Groq or another OpenAI-compatible provider.
