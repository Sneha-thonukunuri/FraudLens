"""MEMBER 1 owns this file.
Currently a keyword MOCK so the pipeline runs end to end without an API key.
TODO (Week 1): replace the body of analyze_text with a structured-output LLM call
that returns the same AnalysisResult. Keep function signatures unchanged."""
from typing import List
from common.schema import AnalysisResult

TACTIC_KEYWORDS = {
    "urgency": ["urgent", "immediately", "within 24 hours", "expire", "last chance", "act now"],
    "authority": ["rbi", "bank officer", "police", "customs", "income tax", "cbi"],
    "fear": ["blocked", "suspended", "arrest", "legal action", "penalty", "freeze"],
    "reward": ["won", "lottery", "prize", "cashback", "bonus", "earn"],
    "isolation": ["don't tell", "do not tell", "keep this secret", "confidential"],
}
CATEGORY_KEYWORDS = {
    "banking_kyc": ["kyc", "pan", "aadhaar", "otp", "account"],
    "upi_payment": ["upi", "collect request", "scan qr", "paytm", "phonepe", "gpay"],
    "phishing": ["click", "link", "verify", "login"],
    "fake_job": ["job offer", "work from home", "registration fee", "part-time", "hiring"],
    "romance": ["my love", "dear", "gift", "stuck at customs", "crypto", "investment"],
}


def analyze_text(text: str) -> AnalysisResult:
    t = text.lower()
    tactics = [k for k, words in TACTIC_KEYWORDS.items() if any(w in t for w in words)]
    cat_hits = {k: sum(w in t for w in words) for k, words in CATEGORY_KEYWORDS.items()}
    category = max(cat_hits, key=cat_hits.get) if any(cat_hits.values()) else "unknown"
    signals = [w for words in CATEGORY_KEYWORDS.values() for w in words if w in t]
    score = min(1.0, 0.18 * (len(tactics) + len(signals)))
    expl = (f"[MOCK] Tactics found: {', '.join(tactics) or 'none'}."
            if tactics else "[MOCK] No manipulation tactics found.")
    return AnalysisResult(source="text", signals=signals, tactics=tactics,
                          category=category if score > 0 else "unknown",
                          score=round(score, 2), explanation=expl)


def analyze_conversation(messages: List[str]) -> AnalysisResult:
    """TODO (Week 3): track escalation across turns (Fraud-R1 style)."""
    if not messages:
        return AnalysisResult(source="conversation", explanation="Empty conversation.")
    per_turn = [analyze_text(m).score for m in messages]
    base = analyze_text(" ".join(messages))
    escalating = len(per_turn) > 1 and per_turn[-1] > per_turn[0]
    signals = base.signals + (["escalation across turns"] if escalating else [])
    score = min(1.0, base.score + (0.15 if escalating else 0))
    return AnalysisResult(source="conversation", signals=signals, tactics=base.tactics,
                          category=base.category, score=round(score, 2),
                          explanation=base.explanation)
