"""MEMBER 3 owns this file.
Basic lexical URL checks. TODO (Week 2): domain age (WHOIS), lookalike-domain
distance, optional page fetching."""
import re
from urllib.parse import urlparse
from common.schema import AnalysisResult

SUSPICIOUS_TLDS = {".xyz", ".top", ".click", ".work", ".live", ".info", ".icu", ".tk"}
BRAND_WORDS = ["sbi", "hdfc", "icici", "axis", "paytm", "phonepe", "gpay", "irctc", "epfo"]


def analyze_url(url: str) -> AnalysisResult:
    if "://" not in url:
        url = "http://" + url
    p = urlparse(url)
    host = (p.hostname or "").lower()
    signals = []
    if p.scheme != "https":
        signals.append("not using HTTPS")
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        signals.append("IP address used as host")
    if "@" in url:
        signals.append("'@' in URL")
    if host.count("-") >= 2:
        signals.append("many hyphens in domain")
    if host.count(".") >= 3:
        signals.append("many subdomains")
    if any(host.endswith(t) for t in SUSPICIOUS_TLDS):
        signals.append("suspicious TLD")
    for b in BRAND_WORDS:
        if b in host and not host.endswith((f"{b}.com", f"{b}.co.in", f"{b}.in")):
            signals.append(f"brand name '{b}' in non-official domain")
    if len(url) > 75:
        signals.append("very long URL")
    score = min(1.0, 0.25 * len(signals))
    return AnalysisResult(source="url", signals=signals, score=round(score, 2),
                          category="phishing" if score >= 0.5 else "unknown",
                          explanation=f"{len(signals)} suspicious URL signal(s) found.")
