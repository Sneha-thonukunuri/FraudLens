"""Tests for system/api.py (Member 3)."""
from fastapi.testclient import TestClient
import system.api as api

client = TestClient(api.app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_url_only_request_works():
    r = client.post("/analyze", json={"url": "http://192.168.1.5/sbi-login"})
    assert r.status_code == 200
    body = r.json()
    assert body["recommendation"] in ("safe", "warn", "block")
    assert "IP address used as host" in body["signals"]


def test_empty_request_is_safe_with_note():
    r = client.post("/analyze", json={})
    assert r.status_code == 200
    assert "no input" in r.json()["explanation"].lower()


def test_blank_text_is_ignored():
    r = client.post("/analyze", json={"text": "   "})
    assert r.status_code == 200
    assert "no input" in r.json()["explanation"].lower()


def test_crashing_analyzer_does_not_crash_api(monkeypatch):
    def boom(_):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(api, "analyze_text", boom)
    r = client.post("/analyze", json={"text": "hello", "url": "http://192.168.1.5"})
    assert r.status_code == 200
    body = r.json()
    assert "text" in body["explanation"] and "failed" in body["explanation"].lower()
    assert "secret internal detail" not in r.text      # no leaking of error details
    assert any("IP address" in s for s in body["signals"])   # URL result still used


def test_all_analyzers_failing_is_not_safe(monkeypatch):
    def boom(_):
        raise RuntimeError("x")
    monkeypatch.setattr(api, "analyze_text", boom)
    r = client.post("/analyze", json={"text": "hello"})
    assert r.status_code == 200
    assert r.json()["recommendation"] == "warn"


def test_too_long_text_rejected():
    r = client.post("/analyze", json={"text": "a" * 10001})
    assert r.status_code == 422


def test_screenshot_wrong_type_rejected():
    r = client.post("/analyze/screenshot",
                    files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_screenshot_empty_file_rejected():
    r = client.post("/analyze/screenshot",
                    files={"file": ("a.png", b"", "image/png")})
    assert r.status_code == 400


def test_screenshot_too_large_rejected():
    big = b"0" * (api.MAX_IMAGE_BYTES + 10)
    r = client.post("/analyze/screenshot", files={"file": ("a.png", big, "image/png")})
    assert r.status_code == 413
    