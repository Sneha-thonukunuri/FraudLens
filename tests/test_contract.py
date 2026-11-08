from fastapi.testclient import TestClient

from common.schema import AnalysisResult
from nlp.analyzer import analyze_text, analyze_conversation
from vision.analyzer import analyze_screenshot
from system.api import app
from system.url_analyzer import analyze_url
from system.fusion import fuse


client = TestClient(app)


def _ok(r):
    assert isinstance(r, AnalysisResult)
    assert 0.0 <= r.score <= 1.0


def test_root_route():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "FraudLens"


def test_text():
    _ok(analyze_text("Your KYC is expired, update immediately or account will be blocked"))


def test_conversation():
    _ok(analyze_conversation(["hi dear", "send gift fee on UPI urgent", "don't tell anyone"]))


def test_screenshot_handles_bad_input():
    _ok(analyze_screenshot(b"not an image"))


def test_url():
    r = analyze_url("http://sbi-kyc-update.xyz/login")
    _ok(r)
    assert r.score > 0.5


def test_fusion():
    v = fuse([analyze_text("urgent: account blocked, verify at link"), analyze_url("http://1.2.3.4/x")])
    assert v.recommendation in {"safe", "warn", "block"}
