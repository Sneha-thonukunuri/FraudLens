"""Minimal LLM client (httpx only, no vendor SDK). Configure through .env:

  LLM_API_KEY    required, otherwise the keyword fallback is used
  LLM_MODEL      required (model name is provider specific, not guessed here)
  LLM_PROVIDER   "anthropic" (default) or "openai" (any OpenAI-compatible API)
  LLM_BASE_URL   optional override, e.g. a self-hosted OpenAI-compatible server
  LLM_TIMEOUT    seconds, default 30
  LLM_MIN_INTERVAL  optional pause in seconds between calls (helps with free-tier
                    rate limits during evaluation), default 0
"""
import os
import time

import httpx

try:                                  # .env is optional
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:                   # pragma: no cover
    pass


RETRY_DELAYS = (2, 5, 10, 20, 30)     # seconds to wait before each retry
BUSY_STATUSES = (429, 500, 502, 503, 504)
MAX_WAIT = 60                          # never sleep longer than this per retry
_last_call = 0.0


class LLMUnavailable(Exception):
    """No key/model configured, or the call failed. Callers fall back to keywords."""


class LLMBusy(LLMUnavailable):
    """Rate limit or overloaded server (429/5xx). Worth retrying after a wait."""

    def __init__(self, message: str, retry_after: float = 0.0):
        super().__init__(message)
        self.retry_after = retry_after


def _parse_retry_after(response) -> float:
    try:
        return max(0.0, float(response.headers.get("retry-after", 0)))
    except (TypeError, ValueError):
        return 0.0


def is_configured() -> bool:
    return bool(os.environ.get("LLM_API_KEY") and os.environ.get("LLM_MODEL"))


def _complete_once(system: str, user: str, max_tokens: int = 600, transport=None) -> str:
    """One attempt. Raises LLMUnavailable on any problem."""
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
    except httpx.HTTPStatusError as e:
        msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        if e.response.status_code in BUSY_STATUSES:
            raise LLMBusy(msg, _parse_retry_after(e.response)) from e
        raise LLMUnavailable(msg) from e
    except Exception as e:            # network, bad JSON shape, ...
        raise LLMUnavailable(f"{type(e).__name__}") from e


def _pace() -> None:
    """Optional minimum gap between calls, from LLM_MIN_INTERVAL."""
    global _last_call
    gap = float(os.environ.get("LLM_MIN_INTERVAL", "0") or 0)
    wait = _last_call + gap - time.monotonic()
    if gap > 0 and wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def complete(system: str, user: str, max_tokens: int = 600, transport=None) -> str:
    """Send one prompt, return the model's text. Busy-server errors (429/5xx) are
    retried, waiting for the provider's Retry-After when it gives one; anything
    else, or running out of retries, raises LLMUnavailable so callers can fall
    back to the keyword analyzer."""
    for attempt in range(len(RETRY_DELAYS) + 1):
        _pace()
        try:
            return _complete_once(system, user, max_tokens, transport)
        except LLMBusy as e:
            if attempt == len(RETRY_DELAYS):
                raise
            time.sleep(min(MAX_WAIT, max(RETRY_DELAYS[attempt], e.retry_after)))