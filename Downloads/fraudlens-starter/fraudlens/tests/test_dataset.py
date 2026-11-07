"""Checks that data/eval_set.jsonl is well formed (Member 3)."""
import json
import pathlib

PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "eval_set.jsonl"
LABELS = {"banking_kyc", "upi_payment", "phishing", "fake_job", "romance", "legitimate"}


def load():
    rows = []
    with open(PATH, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                rows.append(json.loads(line))   # fails with a clear error if a line is bad
    return rows


def test_file_loads_and_is_not_empty():
    assert len(load()) >= 40


def test_ids_are_unique():
    ids = [r["id"] for r in load()]
    assert len(ids) == len(set(ids))


def test_every_row_has_required_fields_and_valid_label():
    for r in load():
        assert isinstance(r["text"], str) and r["text"].strip()
        assert isinstance(r["url"], str)
        assert r["label"] in LABELS, f"bad label in id {r['id']}"
        assert r["difficulty"] in {"easy", "medium", "hard"}


def test_every_category_has_examples():
    labels = {r["label"] for r in load()}
    assert labels == LABELS


def test_has_both_scam_and_legitimate_examples():
    rows = load()
    legit = sum(r["label"] == "legitimate" for r in rows)
    assert 0 < legit < len(rows)