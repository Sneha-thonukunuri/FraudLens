import pytest


@pytest.fixture(autouse=True)
def _no_llm_by_default(monkeypatch):
    """Tests must never call a real LLM. Tests that need one configure it explicitly."""
    for var in ("LLM_API_KEY", "LLM_MODEL", "LLM_PROVIDER", "LLM_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
