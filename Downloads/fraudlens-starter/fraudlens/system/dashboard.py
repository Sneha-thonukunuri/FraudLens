"""MEMBER 3 owns this file. Run from repo root: streamlit run system/dashboard.py"""
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
import streamlit as st
from nlp.analyzer import analyze_text
from vision.analyzer import analyze_screenshot
from system.url_analyzer import analyze_url
from system.fusion import fuse

st.title("FraudLens")
text = st.text_area("Message text")
url = st.text_input("URL")
img = st.file_uploader("Screenshot", type=["png", "jpg", "jpeg"])

if st.button("Analyze"):
    results = []
    if text: results.append(analyze_text(text))
    if url: results.append(analyze_url(url))
    if img: results.append(analyze_screenshot(img.read()))
    v = fuse(results)
    st.metric("Risk score", v.score)
    st.subheader(v.recommendation.upper())
    st.write("Category:", v.category)
    st.write("Tactics:", ", ".join(v.tactics) or "none")
    st.write("Signals:", ", ".join(v.signals) or "none")
    st.write(v.explanation)
