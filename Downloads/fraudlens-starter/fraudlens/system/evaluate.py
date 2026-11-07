"""MEMBER 3: evaluation pipeline.
Run from the project root:  python -m system.evaluate
Compares four approaches on data/eval_set.jsonl (binary task: scam vs legitimate):
  1. keyword_baseline : a plain keyword rule (no analyzers)
  2. url_only         : analyze_url alone
  3. text_only        : analyze_text alone
  4. integrated       : analyze_text + analyze_url combined with fuse()
Results describe THIS dataset only. The dataset is small and synthetic, so the
numbers are prototype indicators, not real-world accuracy."""
import json
import pathlib
import sys
from datetime import datetime

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from nlp.analyzer import analyze_text
from system.url_analyzer import analyze_url
from system.fusion import fuse

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "eval_set.jsonl"
OUT_PATH = ROOT / "data" / "eval_results.json"

# Plain baseline: flag as scam if at least 2 of these words appear.
BASELINE_WORDS = ["urgent", "immediately", "blocked", "suspended", "kyc", "otp", "click",
                  "verify", "winner", "won", "prize", "refund", "pay", "fee", "lottery",
                  "expire", "expires", "bank details", "pin", "deposit"]
BASELINE_MIN_HITS = 2


def load_data(path=DATA_PATH):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def compute_metrics(y_true, y_pred):
    """y_true / y_pred are lists of booleans (True = scam). Returns a dict."""
    tp = sum(t and p for t, p in zip(y_true, y_pred))
    tn = sum((not t) and (not p) for t, p in zip(y_true, y_pred))
    fp = sum((not t) and p for t, p in zip(y_true, y_pred))
    fn = sum(t and (not p) for t, p in zip(y_true, y_pred))

    def div(a, b):
        return round(a / b, 3) if b else 0.0

    precision = div(tp, tp + fp)
    recall = div(tp, tp + fn)
    f1 = round(2 * precision * recall / (precision + recall), 3) if (precision + recall) else 0.0
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "accuracy": div(tp + tn, tp + tn + fp + fn),
            "precision": precision, "recall": recall, "f1": f1,
            "false_positive_rate": div(fp, fp + tn)}


# ---------- the four approaches; each returns (predicted_scam, score) or None on failure ----------
def keyword_baseline(row):
    blob = (row["text"] + " " + row["url"]).lower()
    hits = sum(w in blob for w in BASELINE_WORDS)
    return hits >= BASELINE_MIN_HITS, float(hits)


def url_only(row):
    if not row["url"].strip():
        return False, 0.0           # no URL given: nothing to flag
    v = fuse([analyze_url(row["url"])])
    return v.recommendation != "safe", v.score


def text_only(row):
    v = fuse([analyze_text(row["text"])])
    return v.recommendation != "safe", v.score


def integrated_warn(row):
    results = [analyze_text(row["text"])]
    if row["url"].strip():
        results.append(analyze_url(row["url"]))
    v = fuse(results)
    return v.recommendation != "safe", v.score


def integrated_block(row):
    results = [analyze_text(row["text"])]
    if row["url"].strip():
        results.append(analyze_url(row["url"]))
    v = fuse(results)
    return v.recommendation == "block", v.score


APPROACHES = {
    "keyword_baseline": keyword_baseline,
    "url_only": url_only,
    "text_only": text_only,
    "integrated (warn or block = scam)": integrated_warn,
    "integrated (block only = scam)": integrated_block,
}


def evaluate(rows):
    report = {}
    for name, func in APPROACHES.items():
        y_true, y_pred, wrong, failed = [], [], [], 0
        for row in rows:
            try:
                pred, score = func(row)
            except Exception as e:      # a crashing analyzer must not stop the evaluation
                failed += 1
                print(f"  [{name}] id {row['id']} failed: {type(e).__name__}")
                continue
            truth = row["label"] != "legitimate"
            y_true.append(truth)
            y_pred.append(pred)
            if truth != pred:
                wrong.append({"id": row["id"], "label": row["label"],
                              "predicted_scam": pred, "score": score,
                              "difficulty": row["difficulty"],
                              "kind": "false_positive" if pred else "false_negative",
                              "text": row["text"][:90]})
        m = compute_metrics(y_true, y_pred)
        m["failed_examples"] = failed
        m["errors"] = wrong
        report[name] = m
    return report


def print_report(report, n_rows):
    print(f"\nFraudLens evaluation on {n_rows} examples ({DATA_PATH.name})")
    print("Positive class = scam. Synthetic dataset: indicative only.\n")
    head = f"{'approach':36} {'acc':>5} {'prec':>5} {'rec':>5} {'f1':>5} {'FPR':>5}   TP TN FP FN"
    print(head)
    print("-" * len(head))
    for name, m in report.items():
        print(f"{name:36} {m['accuracy']:>5} {m['precision']:>5} {m['recall']:>5} "
              f"{m['f1']:>5} {m['false_positive_rate']:>5}   "
              f"{m['tp']:>2} {m['tn']:>2} {m['fp']:>2} {m['fn']:>2}")
        if m["failed_examples"]:
            print(f"   (!) {m['failed_examples']} example(s) failed and were excluded")

    main = report["integrated (warn or block = scam)"]
    print("\nConfusion matrix, integrated (warn or block = scam):")
    print("                    predicted scam   predicted safe")
    print(f"  actual scam       {main['tp']:>14}   {main['fn']:>14}")
    print(f"  actual legit      {main['fp']:>14}   {main['tn']:>14}")

    print("\nMisclassified by integrated (warn or block = scam):")
    for e in main["errors"]:
        print(f"  id {e['id']:>2} [{e['kind']}] label={e['label']} "
              f"score={e['score']} difficulty={e['difficulty']}")
        print(f"        {e['text']}")


def main():
    rows = load_data()
    report = evaluate(rows)
    print_report(report, len(rows))
    out = {"run_time": datetime.now().isoformat(timespec="seconds"),
           "dataset": DATA_PATH.name, "n_examples": len(rows), "results": report}
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved full results to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()