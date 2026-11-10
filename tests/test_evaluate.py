"""Tests for the metric calculations in system/evaluate.py (Member 3)."""
from system.evaluate import compute_metrics


def test_perfect_predictions():
    m = compute_metrics([True, True, False, False], [True, True, False, False])
    assert m["accuracy"] == 1.0 and m["f1"] == 1.0 and m["false_positive_rate"] == 0.0


def test_known_confusion_counts():
    # truth: 3 scam, 3 legit.  predictions: 2 scam caught, 1 missed, 1 legit flagged
    y_true = [True, True, True, False, False, False]
    y_pred = [True, True, False, True, False, False]
    m = compute_metrics(y_true, y_pred)
    assert (m["tp"], m["fn"], m["fp"], m["tn"]) == (2, 1, 1, 2)
    assert m["precision"] == 0.667
    assert m["recall"] == 0.667
    assert m["false_positive_rate"] == 0.333


def test_no_predicted_positives_does_not_divide_by_zero():
    m = compute_metrics([True, False], [False, False])
    assert m["precision"] == 0.0 and m["f1"] == 0.0

def test_llm_called_once_per_message_and_fallback_counted(monkeypatch):
    from system import evaluate as ev
    from common.schema import AnalysisResult
    calls = []

    def fake(text):
        calls.append(text)
        return AnalysisResult(source="text", explanation="[MOCK] x")
    monkeypatch.setattr(ev, "analyze_text", fake)
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_MODEL", "m")
    ev._text_cache.clear()
    row = {"text": "hello", "url": ""}
    ev.text_only(row)
    ev.integrated_warn(row)
    ev.integrated_block(row)
    assert calls == ["hello"]
    assert ev.fallback_count() == 1