"""MEMBER 3 owns this file. Combines analyzer outputs into one Verdict.
TODO (Week 3): tune weights/thresholds on your labeled data."""
from typing import List
from common.schema import AnalysisResult, Verdict

WARN_AT, BLOCK_AT = 0.4, 0.7


def fuse(results: List[AnalysisResult]) -> Verdict:
    if not results:
        return Verdict(score=0.0, recommendation="safe", explanation="No input analyzed.")
    scores = [r.score for r in results]
    score = round(min(1.0, 0.6 * max(scores) + 0.4 * sum(scores) / len(scores)), 2)
    rec = "block" if score >= BLOCK_AT else "warn" if score >= WARN_AT else "safe"
    top = max(results, key=lambda r: r.score)
    return Verdict(
        score=score, recommendation=rec, category=top.category,
        tactics=sorted({t for r in results for t in r.tactics}),
        signals=sorted({s for r in results for s in r.signals}),
        explanation=" ".join(r.explanation for r in results if r.explanation),
        details=results,
    )
