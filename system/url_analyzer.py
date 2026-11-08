"""MEMBER 3 owns this file.
Lexical URL checks only. This code never visits the URL, so it is safe from
SSRF. It does NOT check domain age or reputation (no such service is used).
Scores are heuristic risk indicators, not calibrated probabilities."""
import re
from urllib.parse import urlparse
from common.schema import AnalysisResult

SUSPICIOUS_TLDS = (".xyz", ".top", ".click", ".work", ".live", ".info", ".icu", ".tk")
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy"}
BRAND_WORDS = ["sbi", "hdfc", "icici", "axis", "paytm", "phonepe", "gpay", "irctc", "epfo"]
EMBEDDED_MIN_LEN = 5   # brands this long are also flagged when glued inside a word

# Each signal has a hand-chosen weight (heuristic, not tuned on data yet).
W_NO_HTTPS = 0.15
W_IP_HOST = 0.40
W_AT_SIGN = 0.35
W_HYPHENS = 0.10
W_SUBDOMAINS = 0.15
W_TLD = 0.20
W_BRAND = 0.40
W_LONG = 0.10
W_ENCODED = 0.10
W_PUNYCODE = 0.25
W_SHORTENER = 0.20
W_MALFORMED = 0.30


def _result(signals, score, explanation):
    score = round(min(1.0, score), 2)
    return AnalysisResult(
        source="url", signals=signals, score=score,
        category="phishing" if score >= 0.5 else "unknown",
        explanation=explanation,
    )


def _is_official(host: str, brand: str) -> bool:
    """True only for an exact official domain or a real subdomain of it."""
    for d in (f"{brand}.com", f"{brand}.co.in", f"{brand}.in"):
        if host == d or host.endswith("." + d):
            return True
    return False


def analyze_url(url: str) -> AnalysisResult:
    if not isinstance(url, str) or not url.strip():
        return _result([], 0.0, "No URL provided.")

    url = url.strip()
    if "://" not in url:
        url = "http://" + url
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower().rstrip(".")
    except ValueError:
        return _result(["malformed URL"], W_MALFORMED,
                       "Suspicious indicators found: the URL could not be parsed.")
    if not host:
        return _result(["malformed URL"], W_MALFORMED,
                       "Suspicious indicators found: no hostname in the URL.")

    findings = []  # list of (signal text, weight)
    is_ip = re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host) is not None

    if p.scheme != "https":
        findings.append(("not using HTTPS", W_NO_HTTPS))
    if is_ip:
        findings.append(("IP address used as host", W_IP_HOST))
    if "@" in p.netloc:
        findings.append(("'@' in URL", W_AT_SIGN))
    if host.count("-") >= 2:
        findings.append(("many hyphens in domain", W_HYPHENS))
    if not is_ip and host.count(".") >= 3:
        findings.append(("many subdomains", W_SUBDOMAINS))
    if host.endswith(SUSPICIOUS_TLDS):
        findings.append(("suspicious TLD", W_TLD))
    if "xn--" in host:
        findings.append(("punycode (possible lookalike characters)", W_PUNYCODE))
    if host in SHORTENERS:
        findings.append(("URL shortener hides the real destination", W_SHORTENER))
    if re.search(r"%[0-9a-fA-F]{2}", url):
        findings.append(("percent-encoded characters in URL", W_ENCODED))
    if len(url) > 75:
        findings.append(("very long URL", W_LONG))

    words = [w for w in re.split(r"[.\-_]", host) if w]
    for b in BRAND_WORDS:
        appears = b in words or (len(b) >= EMBEDDED_MIN_LEN and any(b in w for w in words))
        if appears and not _is_official(host, b):
            findings.append((f"brand name '{b}' in non-official domain", W_BRAND))

    signals = [s for s, _ in findings]
    score = sum(w for _, w in findings)
    if signals:
        explanation = "Suspicious indicators found: " + "; ".join(signals) + "."
    else:
        explanation = ("No suspicious lexical indicators found. This does not prove "
                       "the URL is safe; domain age and reputation were not checked.")
    return _result(signals, score, explanation)