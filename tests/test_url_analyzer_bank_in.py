"""Tests for restricted-suffix handling (.bank.in / .fin.in) in system/url_analyzer.py.
Strings only; no website is ever visited."""
from system.url_analyzer import analyze_url, _under_protected_suffix


def brand_signals(r):
    return [s for s in r.signals if "brand name" in s]


def test_bank_in_domain_is_not_flagged():
    r = analyze_url("https://www.icici.bank.in")
    assert brand_signals(r) == []
    assert "many subdomains" not in r.signals
    assert r.score == 0.0


def test_bank_in_without_www_is_not_flagged():
    assert analyze_url("https://hdfc.bank.in").score == 0.0


def test_fin_in_domain_is_not_flagged():
    assert brand_signals(analyze_url("https://paytm.fin.in")) == []


def test_bank_in_as_prefix_of_evil_domain_is_still_flagged():
    r = analyze_url("https://icici.bank.in.verify-kyc.xyz")
    assert brand_signals(r) != []
    assert "suspicious TLD" in r.signals


def test_hyphenated_lookalike_is_still_flagged():
    assert brand_signals(analyze_url("https://icici-bank.in")) != []


def test_fake_bank_dot_in_lookalike_is_still_flagged():
    assert brand_signals(analyze_url("https://icici.fakebank.in")) != []


def test_bare_suffix_is_not_trusted():
    assert _under_protected_suffix("bank.in") is False


def test_bank_in_with_http_still_flags_missing_https():
    assert "not using HTTPS" in analyze_url("http://icici.bank.in").signals
