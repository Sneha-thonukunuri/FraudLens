"""Tests for system/fusion.py (Member 3). Uses mock AnalysisResult objects."""
from common.schema import AnalysisResult
from system.fusion import fuse


def mock(source="text", score=0.0, category="unknown", signals=None, tactics=None):
    return AnalysisResult(source=source, score=score, category=category,
                          signals=signals or [], tactics=tactics or [],
                          explanation=f"{source} explanation")


UNREADABLE = AnalysisResult(
    source="screenshot", score=0.0,
    explanation="[MOCK] No text extracted (OCR unavailable or empty image).")


def test_empty_input_is_safe_with_note():
    v = fuse([])
    assert v.recommendation == "safe"
    assert "no input" in v.explanation.lower()


def test_all_analyzers_failed_is_not_reported_safe():
    v = fuse([], errors=["text", "url"])
    assert v.recommendation == "warn"
    assert "not a safety" in v.explanation.lower()


def test_low_scores_give_safe():
    assert fuse([mock(score=0.0), mock("url", 0.1)]).recommendation == "safe"


def test_high_scores_give_block():
    v = fuse([mock(score=0.9), mock("url", 0.8)])
    assert v.recommendation == "block"
    assert v.score >= 0.7


def test_one_strong_warning_not_hidden_by_clean_analyzer():
    v = fuse([mock(score=0.9), mock("url", 0.0)])
    assert v.recommendation in ("warn", "block")


def test_score_stays_in_range():
    v = fuse([mock(score=1.0), mock("url", 1.0), mock("screenshot", 1.0)])
    assert 0.0 <= v.score <= 1.0


def test_duplicate_signals_counted_once():
    a = mock(score=0.5, signals=["fake link"])
    b = mock("screenshot", 0.5, signals=["fake link", "urgent wording"])
    v = fuse([a, b])
    assert v.signals.count("fake link") == 1
    assert len(v.signals) == 2


def test_tactics_are_merged():
    v = fuse([mock(tactics=["urgency"]), mock("url", tactics=["fear"])])
    assert v.tactics == ["fear", "urgency"]


def test_specific_category_preferred_over_unknown():
    v = fuse([mock(score=0.2, category="banking_kyc"), mock("url", 0.6, "unknown")])
    assert v.category == "banking_kyc"


def test_explanation_names_sources_and_gives_advice():
    v = fuse([mock(score=0.9), mock("url", 0.8)])
    assert "[text]" in v.explanation and "[url]" in v.explanation
    assert "do not click" in v.explanation.lower()


def test_failed_analyzer_is_mentioned():
    v = fuse([mock(score=0.1)], errors=["screenshot"])
    assert "screenshot" in v.explanation
    assert "failed" in v.explanation.lower()


def test_details_keep_original_results():
    r = [mock(score=0.3), mock("url", 0.2)]
    assert len(fuse(r).details) == 2


def test_unreadable_screenshot_is_not_reported_safe():
    v = fuse([UNREADABLE])
    assert v.recommendation == "warn"
    assert "not a safety" in v.explanation.lower()


def test_unreadable_screenshot_does_not_dilute_other_scores():
    v = fuse([mock(score=0.9), UNREADABLE])
    assert v.score == fuse([mock(score=0.9)]).score