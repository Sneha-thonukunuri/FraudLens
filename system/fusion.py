"""MEMBER 3 owns this file. Combines analyzer outputs into one Verdict.
The score is a heuristic prototype risk indicator, NOT a calibrated probability.
Weights and thresholds below are hand-chosen and must be tuned/evaluated
on our labeled dataset before we make any accuracy claims."""
from typing import List, Optional
from common.schema import AnalysisResult, Verdict

WARN_AT, BLOCK_AT = 0.4, 0.7
# Score = W_MAX * (highest score) + W_MEAN * (average score).
# The max term stops one clean analyzer from hiding a strong warning;
# the mean term rewards cases where several analyzers agree.
W_MAX, W_MEAN = 0.6, 0.4

# Stopgap: phrases an analyzer uses when it could not analyze its input.
# TODO: replace with an explicit field once the team agrees on a schema change.
INCONCLUSIVE_MARKERS = ("no text extracted", "no readable text")

ADVICE = {
    "safe": ("No strong scam indicators were found, but this is not a guarantee. "
             "Stay careful with links, payments and OTP requests."),
    "warn": ("Be careful. Do not click links, share OTPs or passwords, or send money "
             "until you verify through the official website, app or helpline."),
    "block": ("High risk. Do not click links, reply, pay, or share any details. "
              "Verify only through the official channel and report it if you can."),
}


def _inconclusive(r: AnalysisResult) -> bool:
    """True if the analyzer produced nothing because it could not read its input."""
    # Look in the explanation AND the signals: the vision analyzer reports an
    # empty OCR result with extra visual signals, so signals are not always empty.
    text = (r.explanation + " " + " ".join(r.signals)).lower()
    return r.score == 0.0 and any(m in text for m in INCONCLUSIVE_MARKERS)


def _pick_category(results: List[AnalysisResult]) -> str:
    """Prefer the highest-scoring result that has a specific scam category."""
    specific = [r for r in results if r.category not in ("unknown", "legitimate")]
    pool = specific or results
    return max(pool, key=lambda r: r.score).category


def fuse(results: List[AnalysisResult], errors: Optional[List[str]] = None) -> Verdict:
    errors = list(errors or [])
    usable = []
    for r in results:
        if _inconclusive(r):
            errors.append(r.source)      # treated like a failed analyzer
        else:
            usable.append(r)

    if not usable:
        if errors:
            return Verdict(
                score=0.0, recommendation="warn", details=results,
                explanation=("Analysis failed for: " + ", ".join(errors) +
                             ". No result is available, so this is NOT a safety "
                             "confirmation. " + ADVICE["warn"]))
        return Verdict(score=0.0, recommendation="safe",
                       explanation="No input was analyzed.")

    scores = [min(1.0, max(0.0, r.score)) for r in usable]
    score = round(min(1.0, W_MAX * max(scores) + W_MEAN * sum(scores) / len(scores)), 2)
    rec = "block" if score >= BLOCK_AT else "warn" if score >= WARN_AT else "safe"

    parts = [f"[{r.source}] {r.explanation}" for r in usable if r.explanation]
    explanation = " ".join(parts + [ADVICE[rec]])
    if errors:
        explanation += (" Note: these analyzers failed or could not read their input "
                        "and were not counted: " + ", ".join(errors) + ".")

    return Verdict(
        score=score, recommendation=rec, category=_pick_category(usable),
        tactics=sorted({t for r in usable for t in r.tactics}),
        signals=sorted({s for r in usable for s in r.signals}),  # duplicates removed
        explanation=explanation, details=results,
    )