"""Tests for system/url_analyzer.py (Member 3).
These tests only analyze strings. They never visit any website."""
from system.url_analyzer import analyze_url


def brand_signals(result):
    return [s for s in result.signals if "brand name" in s]


# ---------- Output shape ----------
def test_result_shape():
    r = analyze_url("https://www.example.com")
    assert r.source == "url"
    assert 0.0 <= r.score <= 1.0


# ---------- HTTPS and IP ----------
def test_http_is_flagged():
    assert "not using HTTPS" in analyze_url("http://example.com").signals


def test_https_not_flagged_for_missing_https():
    assert "not using HTTPS" not in analyze_url("https://example.com").signals


def test_ip_host_is_flagged():
    assert "IP address used as host" in analyze_url("http://192.168.10.5/login").signals


def test_ip_host_not_called_many_subdomains():
    assert "many subdomains" not in analyze_url("http://192.168.1.5/x").signals


# ---------- Brand checks ----------
def test_official_domain_not_flagged():
    assert brand_signals(analyze_url("https://www.sbi.co.in")) == []
    assert brand_signals(analyze_url("https://sbi.com")) == []


def test_brand_in_fake_subdomain_is_flagged():
    assert brand_signals(analyze_url("https://sbi.com.verify-login.xyz")) != []


def test_innocent_word_containing_brand_letters_not_flagged():
    assert brand_signals(analyze_url("https://www.taxis-booking.com")) == []


def test_brand_as_separate_word_is_flagged():
    assert brand_signals(analyze_url("https://sbi-kyc-update.com")) != []


def test_long_brand_glued_into_word_is_flagged():
    assert brand_signals(analyze_url("https://paytmsecure.in")) != []


def test_fake_domain_ending_in_official_name_not_trusted():
    assert brand_signals(analyze_url("https://paytm.com.evil.xyz")) != []


def test_trailing_dot_on_official_domain_still_official():
    assert brand_signals(analyze_url("https://sbi.com.")) == []


# ---------- Other signals ----------
def test_shortener_flagged():
    assert any("shortener" in s for s in analyze_url("https://bit.ly/abc").signals)


def test_at_sign_flagged():
    assert "'@' in URL" in analyze_url("http://sbi.co.in@evil.xyz/login").signals


def test_trailing_dot_does_not_hide_suspicious_tld():
    assert "suspicious TLD" in analyze_url("http://evil.xyz./login").signals


# ---------- Scores ----------
def test_clean_url_has_low_score():
    assert analyze_url("https://www.wikipedia.org").score == 0.0


def test_risky_url_scores_higher_than_clean_url():
    risky = analyze_url("http://192.168.1.5/sbi-login")
    clean = analyze_url("https://www.wikipedia.org")
    assert risky.score > clean.score


# ---------- Bad input must not crash ----------
def test_empty_url_does_not_crash():
    r = analyze_url("")
    assert r.score == 0.0
    assert "no url" in r.explanation.lower()


def test_none_url_does_not_crash():
    assert analyze_url(None).score == 0.0