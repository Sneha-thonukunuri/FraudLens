"""Minimal LLM client (httpx only, no vendor SDK). Configure through .env:

  LLM_API_KEY    required, otherwise the keyword fallback is used
  LLM_MODEL      required (model name is provider specific, not guessed here)
  LLM_PROVIDER   "anthropic" (default) or "openai" (any OpenAI-compatible API)
  LLM_BASE_URL   optional override, e.g. a self-hosted OpenAI-compatible server
  LLM_TIMEOUT    seconds, default 30
"""
import os

import httpx

try:                                  # .env is optional
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:                   # pragma: no cover
    pass


class LLMUnavailable(Exception):
    """No key/model configured, or the call failed. Callers fall back to keywords."""


def is_configured() -> bool:
    return bool(os.environ.get("LLM_API_KEY") and os.environ.get("LLM_MODEL"))


def complete(system: str, user: str, max_tokens: int = 600, transport=None) -> str:
    """Send one prompt, return the model's text. Raises LLMUnavailable on any problem."""
    if not is_configured():
        raise LLMUnavailable("LLM_API_KEY / LLM_MODEL not set")
    key, model = os.environ["LLM_API_KEY"], os.environ["LLM_MODEL"]
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    timeout = float(os.environ.get("LLM_TIMEOUT", "30"))
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            if provider == "anthropic":
                base = os.environ.get("LLM_BASE_URL", "https://api.anthropic.com")
                r = client.post(
                    f"{base}/v1/messages",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    json={"model": model, "max_tokens": max_tokens, "system": system,
                          "messages": [{"role": "user", "content": user}]})
                r.raise_for_status()
                return "".join(b.get("text", "") for b in r.json()["content"]
                               if b.get("type") == "text")
            if provider == "openai":
                base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
                r = client.post(
                    f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": model, "max_tokens": max_tokens,
                          "response_format": {"type": "json_object"},
                          "messages": [{"role": "system", "content": system},
                                       {"role": "user", "content": user}]})
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            raise LLMUnavailable(f"unknown LLM_PROVIDER '{provider}'")
    except LLMUnavailable:
        raise
    except Exception as e:            # network, HTTP status, bad JSON shape, ...
        raise LLMUnavailable(f"{type(e).__name__}") from e
