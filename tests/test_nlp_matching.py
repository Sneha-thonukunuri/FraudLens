from nlp.analyzer import analyze_text


def test_substrings_inside_words_do_not_match():
    r = analyze_text("Our company is known for its panel plans")
    assert r.signals == []
    assert r.tactics == []
    assert r.category == "unknown"


def test_whole_words_still_match():
    r = analyze_text("Update your PAN and Aadhaar KYC now or the account is blocked")
    assert {"pan", "aadhaar", "kyc", "account"} <= set(r.signals)
    assert "fear" in r.tactics
    assert r.category == "banking_kyc"


def test_simple_word_endings_match():
    assert "urgency" in analyze_text("Your offer expired, act now").tactics
    assert "link" in analyze_text("Click the links below").signals


def test_curly_apostrophe_matches_isolation_phrase():
    assert "isolation" in analyze_text("Please don\u2019t tell anyone").tactics
