import pytest


@pytest.fixture(autouse=True)
def _no_llm_by_default(monkeypatch):
    """Tests must never call a real LLM or depend on the developer's .env.
    Tests that need an LLM configure it explicitly."""
    for var in ("LLM_API_KEY", "LLM_MODEL", "LLM_PROVIDER", "LLM_BASE_URL",
                "LLM_TIMEOUT", "LLM_MIN_INTERVAL"):
        monkeypatch.delenv(var, raising=False)
