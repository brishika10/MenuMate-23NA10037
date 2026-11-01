"""OpenAI-compatible client. Provider settings come only from LLM_API_KEY / LLM_BASE_URL / LLM_MODEL."""
import json
import os
import random
import time

from openai import AuthenticationError, BadRequestError, NotFoundError, OpenAI, PermissionDeniedError

_client = None


def model_name() -> str:
    return os.environ.get("LLM_MODEL", "")


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ.get("LLM_API_KEY"), base_url=os.environ.get("LLM_BASE_URL") or None,
                         timeout=15.0, max_retries=0)
    return _client


class Usage:
    def __init__(self):
        self.prompt = 0
        self.completion = 0


def chat_json(messages: list[dict], usage: Usage, temperature: float = 0.0, max_tokens: int = 500) -> dict:
    """One JSON-mode completion with retry + exponential backoff on API errors / rate limits.
    Raises after the last attempt; callers fall back to deterministic code."""
    last = None
    for attempt in range(3):
        try:
            r = client().chat.completions.create(
                model=model_name(), messages=messages, temperature=temperature, max_tokens=max_tokens,
                response_format={"type": "json_object"})
            if r.usage:
                usage.prompt += r.usage.prompt_tokens or 0
                usage.completion += r.usage.completion_tokens or 0
            return json.loads(r.choices[0].message.content or "")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON from model: {e}") from e
        except (AuthenticationError, PermissionDeniedError, NotFoundError, BadRequestError) as e:
            raise RuntimeError(f"LLM call failed (not retryable): {e}") from e
        except Exception as e:  # rate limit, timeout, 5xx
            last = e
            time.sleep(min(8, 2 ** attempt) + random.random() * 0.3)
    raise RuntimeError(f"LLM call failed: {last}")
