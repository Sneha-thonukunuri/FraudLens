# """MEMBER 3 owns this file. Run from repo root: streamlit run system/dashboard.py"""
# import sys, pathlib
# sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
# import streamlit as st
# from nlp.analyzer import analyze_text
# from vision.analyzer import analyze_screenshot
# from system.url_analyzer import analyze_url
# from system.fusion import fuse

# st.title("FraudLens")
# text = st.text_area("Message text")
# url = st.text_input("URL")
# img = st.file_uploader("Screenshot", type=["png", "jpg", "jpeg"])

# if st.button("Analyze"):
#     results = []
#     if text: results.append(analyze_text(text))
#     if url: results.append(analyze_url(url))
#     if img: results.append(analyze_screenshot(img.read()))
#     v = fuse(results)
#     st.metric("Risk score", v.score)
#     st.subheader(v.recommendation.upper())
#     st.write("Category:", v.category)
#     st.write("Tactics:", ", ".join(v.tactics) or "none")
#     st.write("Signals:", ", ".join(v.signals) or "none")
#     st.write(v.explanation)


"""MEMBER 3 owns this file. Run from repo root: streamlit run system/dashboard.py"""
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
import streamlit as st
from nlp.analyzer import analyze_text, analyze_conversation
from vision.analyzer import analyze_screenshot
from system.url_analyzer import analyze_url
from system.fusion import fuse
from system.api import _run, MAX_IMAGE_BYTES   # same failure isolation as the API

st.set_page_config(page_title="FraudLens", page_icon="🔍")
st.title("FraudLens")
st.caption("AI-based digital scam detection (prototype). The risk score is a heuristic "
           "indicator, not a probability, and no result guarantees a message is safe or a scam.")

text = st.text_area("Single message (SMS, email, WhatsApp)", max_chars=10000)
convo = st.text_area("Conversation (one message per line, oldest first)", max_chars=10000)
url = st.text_input("URL (it is only analyzed as text and is never opened)", max_chars=2048)
img = st.file_uploader("Screenshot", type=["png", "jpg", "jpeg"])

if st.button("Analyze"):
    results, errors = [], []
    if text.strip():
        _run("text", analyze_text, text, results, errors)
    messages = [m.strip() for m in convo.splitlines() if m.strip()]
    if messages:
        _run("conversation", analyze_conversation, messages, results, errors)
    if url.strip():
        _run("url", analyze_url, url, results, errors)
    if img is not None:
        data = img.read()
        if len(data) > MAX_IMAGE_BYTES:
            st.error("Image is too large (max 5 MB).")
        else:
            _run("screenshot", analyze_screenshot, data, results, errors)

    if not results and not errors:
        st.info("Please enter a message, conversation, URL or screenshot.")
        st.stop()

    v = fuse(results, errors)

    banner = {"safe": st.success, "warn": st.warning, "block": st.error}[v.recommendation]
    banner(f"Recommendation: {v.recommendation.upper()}")
    col1, col2 = st.columns(2)
    col1.metric("Risk indicator (0 to 1)", v.score)
    col2.metric("Likely category", v.category.replace("_", " "))
    st.progress(min(1.0, max(0.0, v.score)))

    for name in errors:
        st.warning(f"The '{name}' analyzer failed and was not counted in this result.")

    st.subheader("Why?")
    st.write(v.explanation)
    st.write("**Manipulation tactics:**", ", ".join(v.tactics) or "none detected")
    if v.signals:
        st.write("**Warning signals:**")
        for s in v.signals:
            st.write(f"- {s}")
    else:
        st.write("**Warning signals:** none detected")

    with st.expander("Breakdown by analyzer"):
        for r in v.details:
            st.write(f"**{r.source}**: score {r.score}, category {r.category.replace('_', ' ')}")
            st.caption(r.explanation)
