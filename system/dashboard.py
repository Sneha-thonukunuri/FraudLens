"""
FraudLens - Cybersecurity Command Center
Run from repository root:
    python -m streamlit run system/dashboard.py

This dashboard uses the existing analyzer interfaces and fusion engine.
It does not change Gemini configuration, analyzer code, or risk thresholds.
"""
import textwrap
import sys
import pathlib
import html
import json
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from nlp.analyzer import analyze_text, analyze_conversation
from vision.analyzer import analyze_screenshot
from system.url_analyzer import analyze_url
from system.fusion import fuse
from system.api import _run, MAX_IMAGE_BYTES


# -------------------------------------------------------------------
# PAGE CONFIG + THEME
# -------------------------------------------------------------------

st.set_page_config(
    page_title="FraudLens | Security Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: Inter, sans-serif; }
.stApp { background: #080d18; color: #e5e7eb; }
[data-testid="stSidebar"] {
    background: #211f1e;
    border-right: 1px solid #393532;
}
[data-testid="stSidebar"] * { color: #dbeafe; }
.main .block-container { max-width: 1500px; padding-top: 1.6rem; }
h1, h2, h3 { color: #f8fafc !important; font-weight: 750 !important; }
p, label { color: #cbd5e1; }
.hero {
    background: transparent;
    border: 0; border-radius: 0;
    padding: 0 0 8px 0; margin-bottom: 16px;
}
.hero-title { color:#10d5f5; font-size:30px; font-weight:800; }
.hero-sub { color:#a5c4ed; font-size:13px; margin-top:7px; }
.metric-card {
    background: #101626;
    border:1px solid #263750; border-radius:9px;
    padding:15px; min-height:92px;
}
.metric-label { color:#94a3b8; font-size:11px; text-transform:uppercase; }
.metric-value { color:#f8fafc; font-size:27px; font-weight:800; margin-top:8px; }
.metric-note { color:#64748b; font-size:10px; margin-top:4px; }
.panel {
    background:#111c30; border:1px solid #263750;
    border-radius:12px; padding:17px; margin-bottom:12px;
}
div.stButton > button {
    background:#211f1e;
    color:#e5e7eb; border:1px solid #4a4540; border-radius:7px; font-weight:600;
}
div.stButton > button:hover { color:#22d3ee; border:1px solid #22d3ee; background:#292623; }
div[data-testid="stMetric"] {
    background:#111c30; border:1px solid #263750;
    padding:12px; border-radius:10px;
}
div[data-testid="stExpander"] {
    background:#111c30; border:1px solid #263750; border-radius:9px;
}
.highlight-danger {
    background:#7f1d1d; color:#fecaca; border-radius:4px;
    padding:2px 4px; font-weight:700;
}
.highlight-warning {
    background:#713f12; color:#fde68a; border-radius:4px;
    padding:2px 4px; font-weight:700;
}
.small-muted { color:#94a3b8; font-size:11px; }
hr { border-color:#263750; }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------------
# SESSION STATE
# -------------------------------------------------------------------

for key, default in {
    "history": [],
    "latest": None,
    "latest_input_text": "",
    "demo_text": "",
    "demo_run_error": None,
    "demo_last_label": "",
    "feedback_log": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# -------------------------------------------------------------------
# DATA + DISPLAY HELPERS
# -------------------------------------------------------------------

def fmt_category(value):
    return str(value or "unknown").replace("_", " ").title()


def metric_card(label, value, note=""):
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{html.escape(str(label))}</div>'
        f'<div class="metric-value">{html.escape(str(value))}</div>'
        f'<div class="metric-note">{html.escape(str(note))}</div></div>',
        unsafe_allow_html=True,
    )


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_eval_results():
    return load_json(ROOT / "data" / "eval_results.json")


def load_eval_dataset():
    path = ROOT / "data" / "eval_set.jsonl"
    rows = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        return []
    return rows


def add_to_history(verdict, input_type, original_text=""):
    entry = {
        "time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "input_type": input_type,
        "score": float(verdict.score),
        "recommendation": verdict.recommendation,
        "category": verdict.category,
        "explanation": verdict.explanation,
        "signals": list(verdict.signals),
        "tactics": list(verdict.tactics),
        "original_text": original_text,
        "details": [
            {
                "source": r.source,
                "score": float(r.score),
                "category": r.category,
                "explanation": r.explanation,
                "signals": list(r.signals),
                "tactics": list(r.tactics),
            }
            for r in verdict.details
        ],
    }
    st.session_state.latest = entry
    st.session_state.latest_input_text = original_text
    st.session_state.history.insert(0, entry)


def highlight_evidence(text, signals):
    """Highlight exact signal phrases only when they occur in the submitted text."""
    escaped = html.escape(str(text))
    terms = sorted(
        {str(s).strip() for s in signals if str(s).strip() and len(str(s).strip()) > 2},
        key=len,
        reverse=True,
    )
    for term in terms:
        safe_term = html.escape(term)
        escaped = __import__("re").sub(
            __import__("re").escape(safe_term),
            lambda m: f'<span class="highlight-danger">{m.group(0)}</span>',
            escaped,
            flags=__import__("re").IGNORECASE,
        )
    return escaped


def extract_text_evidence(text):
    """
    Find exact suspicious phrases in submitted text for explainability.
    This is a transparent UI-side phrase matcher, separate from analyzer scoring.
    """
    if not text:
        return []

    patterns = [
        ("Credential request", r"\b(?:share|send|provide|enter|confirm)\s+(?:your\s+)?(?:otp|one[- ]time password|pin|upi pin|password|cvv)\b"),
        ("Urgency / pressure", r"\b(?:immediately|urgent(?:ly)?|within\s+\d+\s*(?:minutes?|hours?)|act now|last warning|final warning)\b"),
        ("Account threat", r"\b(?:account|card|upi)\s+(?:will be|has been|is)\s+(?:blocked|suspended|locked|disabled)\b"),
        ("Link / verification request", r"\b(?:click|tap|open)\s+(?:the\s+)?(?:link|here|below)\b|\b(?:verify|update|reactivate)\s+(?:your\s+)?(?:account|kyc|details)\b"),
        ("Payment pressure", r"\b(?:pay|transfer|send)\s+(?:₹|rs\.?|inr)?\s*[\d,]+|\b(?:processing fee|registration fee|security deposit)\b"),
        ("Prize / reward claim", r"\b(?:you have won|claim your prize|cashback|reward points|free gift|lottery winner)\b"),
        ("Job scam indicators", r"\b(?:work from home|earn\s+₹?\s*[\d,]+|no experience required|pay to apply|job offer)\b"),
        ("Secrecy / impersonation", r"\b(?:do not tell anyone|keep this confidential|official support|bank representative|customer care)\b"),
    ]

    import re
    found = []
    seen = set()
    for label, pattern in patterns:
        for match in re.finditer(pattern, str(text), flags=re.IGNORECASE):
            phrase = match.group(0).strip()
            key = (label, phrase.lower())
            if key not in seen:
                seen.add(key)
                found.append({
                    "type": label,
                    "phrase": phrase,
                    "start": match.start(),
                    "end": match.end(),
                })
    return found


def highlight_matched_phrases(text, evidence):
    """Escape user input and highlight all non-overlapping exact phrase matches."""
    source = str(text)
    pieces = []
    cursor = 0
    for item in sorted(evidence, key=lambda x: x["start"]):
        start, end = item["start"], item["end"]
        if start < cursor:
            continue
        pieces.append(html.escape(source[cursor:start]))
        phrase = html.escape(source[start:end])
        label = html.escape(item["type"])
        pieces.append(
            f'<mark class="evidence-mark" title="{label}">{phrase}</mark>'
        )
        cursor = end
    pieces.append(html.escape(source[cursor:]))
    return "".join(pieces)


def show_verdict(entry, key_suffix="result"):
    if not entry:
        return

    status = entry["recommendation"].upper()
    icon = {"SAFE": "🟢", "WARN": "🟡", "BLOCK": "🔴"}.get(status, "⚪")

    st.markdown("---")
    st.subheader("🛡️ Threat Intelligence Assessment")

    a, b, c, d = st.columns(4)
    with a:
        metric_card("Assessed risk score", f"{entry['score'] * 100:.0f}/100",
                    "Heuristic indicator, not probability")
    with b:
        metric_card("Severity level", status, "Based on existing fusion thresholds")
    with c:
        metric_card("Threat category", fmt_category(entry["category"]), "Likely category")
    with d:
        metric_card("Recommended action", status, "FraudLens recommendation")

    st.progress(min(1.0, max(0.0, entry["score"])))
    st.markdown(f"### {icon} {status} ASSESSMENT")

    st.markdown("#### 🔎 Explainable AI Justification")
    st.markdown(
        f'<div class="panel">{html.escape(entry["explanation"])}</div>',
        unsafe_allow_html=True,
    )

    # Explainable text evidence: exact phrases found in the submitted text.
    if entry.get("original_text"):
        evidence = extract_text_evidence(entry["original_text"])
        st.markdown("#### 🧩 Explainable Text Evidence")
        st.caption(
            "Highlighted phrases are matches from a transparent phrase-pattern list. "
            "They help explain the message, but they do not independently determine the risk score."
        )
        st.markdown(
            '<div class="panel" style="line-height:2.0;">'
            + highlight_matched_phrases(entry["original_text"], evidence)
            + '</div>',
            unsafe_allow_html=True,
        )
        if evidence:
            st.markdown("**Why these phrases deserve attention**")
            evidence_rows = [
                {"Indicator": item["type"], "Matched phrase": item["phrase"]}
                for item in evidence
            ]
            st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
        else:
            st.info(
                "No phrases from the explainability pattern list matched this text. "
                "The NLP analyzer may still report other signals or tactics below."
            )

    # Visual explanation for this exact analysis result (not benchmark data).
    st.markdown("#### 📊 Visual Risk & Evidence Breakdown")
    gauge_col, evidence_col = st.columns(2)

    with gauge_col:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=entry["score"] * 100,
            number={"suffix": "/100", "font": {"size": 30, "color": "#f8fafc"}},
            title={"text": "Risk score indicator", "font": {"color": "#cbd5e1", "size": 15}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#94a3b8"},
                "bar": {"color": "#ef4444" if entry["score"] >= 0.7 else
                        "#f59e0b" if entry["score"] >= 0.4 else "#10b981"},
                "bgcolor": "#101626",
                "bordercolor": "#263750",
                "steps": [
                    {"range": [0, 40], "color": "rgba(16,185,129,0.18)"},
                    {"range": [40, 70], "color": "rgba(245,158,11,0.18)"},
                    {"range": [70, 100], "color": "rgba(239,68,68,0.18)"},
                ],
                "threshold": {
                    "line": {"color": "#f8fafc", "width": 3},
                    "thickness": 0.8,
                    "value": entry["score"] * 100,
                },
            },
        ))
        gauge.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            height=270,
            margin=dict(t=55, b=10, l=25, r=25),
        )
        st.plotly_chart(gauge, use_container_width=True, key=f"risk_gauge_{key_suffix}")

    with evidence_col:
        evidence_labels = ["Threat signals", "Social-engineering tactics"]
        evidence_values = [len(entry["signals"]), len(entry["tactics"])]
        if sum(evidence_values) > 0:
            evidence_fig = go.Figure(go.Pie(
                labels=evidence_labels,
                values=evidence_values,
                hole=0.58,
                textinfo="label+value+percent",
                marker={"colors": ["#06b6d4", "#a78bfa"]},
            ))
            evidence_fig.update_layout(
                template="plotly_dark",
                title={"text": "Detected evidence composition", "font": {"size": 15}},
                paper_bgcolor="rgba(0,0,0,0)",
                height=270,
                margin=dict(t=55, b=10, l=10, r=10),
                showlegend=False,
            )
            st.plotly_chart(
                evidence_fig, use_container_width=True,
                key=f"evidence_pie_{key_suffix}",
            )
        else:
            st.info("No signals or tactics were reported for this input.")

    if entry["details"]:
        analyzer_names = [str(d["source"]).replace("_", " ").title()
                          for d in entry["details"]]
        analyzer_scores = [float(d["score"]) * 100 for d in entry["details"]]
        analyzer_fig = go.Figure(go.Bar(
            x=analyzer_scores,
            y=analyzer_names,
            orientation="h",
            text=[f"{score:.0f}/100" for score in analyzer_scores],
            textposition="outside",
            marker={"color": "#06b6d4"},
        ))
        analyzer_fig.update_layout(
            template="plotly_dark",
            title={"text": "Analyzer risk indicators", "font": {"size": 15}},
            xaxis={"title": "Analyzer score (0–100)", "range": [0, 110]},
            yaxis={"autorange": "reversed"},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=max(190, 90 + 55 * len(analyzer_names)),
            margin=dict(t=50, b=35, l=15, r=35),
        )
        st.plotly_chart(
            analyzer_fig, use_container_width=True,
            key=f"analyzer_bars_{key_suffix}",
        )

    st.caption(
        "These charts describe this analysis only. The risk score is a heuristic indicator, "
        "not a calibrated probability; evidence counts are counts, not confidence percentages."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Detected threat signals**")
        if entry["signals"]:
            for signal in entry["signals"]:
                st.markdown(f"- ⚠️ {signal}")
        else:
            st.caption("No warning signals reported by the analyzers.")
    with right:
        st.markdown("**Psychological and social-engineering tactics**")
        if entry["tactics"]:
            for tactic in entry["tactics"]:
                st.markdown(f"- {fmt_category(tactic)}")
        else:
            st.caption("No manipulation tactics reported.")

    st.markdown("#### 📋 Actionable Security Recommendations")
    recommendations = {
        "safe": [
            "Remain cautious with unexpected links and attachments.",
            "Never share OTPs, passwords, UPI PINs or card security details.",
            "Verify unusual requests through official channels.",
        ],
        "warn": [
            "Do not click links or download attachments until verified.",
            "Do not share OTPs, passwords or payment credentials.",
            "Contact the organization using its official app or website.",
        ],
        "block": [
            "Do not click, reply, pay or share personal information.",
            "Stop communication and independently verify the sender.",
            "Report the suspicious message to the relevant organization.",
        ],
    }
    for item in recommendations.get(entry["recommendation"], recommendations["warn"]):
        st.markdown(
            f'<div class="panel" style="padding:9px 12px;margin-bottom:6px;">'
            f'🔹 {html.escape(item)}</div>',
            unsafe_allow_html=True,
        )

    # Explain URL-specific lexical indicators when a URL analyzer ran.
    url_details = [
        d for d in entry["details"]
        if "url" in str(d.get("source", "")).lower()
    ]
    if url_details:
        st.markdown("#### 🔗 URL Intelligence Breakdown")
        url_labels = {
            "no_https": ("No HTTPS encryption", "The URL does not use HTTPS."),
            "ip_host": ("IP address host", "An IP address is used instead of a recognizable domain."),
            "at_symbol": ("At-sign in URL", "An @ character can obscure the actual destination."),
            "many_hyphens": ("Multiple hyphens", "Unusual hyphen patterns can appear in deceptive domains."),
            "many_dots": ("Multiple subdomains", "Several subdomains can make a deceptive address look familiar."),
            "suspicious_tld": ("Suspicious domain extension", "The extension is on the URL analyzer's heuristic watchlist."),
            "brand_impersonation": ("Possible brand impersonation", "A brand-like term appears outside an official domain."),
            "punycode": ("Punycode domain", "The domain uses an encoded internationalized-domain form."),
            "url_shortener": ("URL shortener", "The final destination is hidden behind a shortened link."),
            "percent_encoding": ("Percent encoding", "Encoded characters may make the address harder to inspect."),
            "long_url": ("Unusually long URL", "Long URLs can contain confusing paths or parameters."),
            "malformed_url": ("Malformed URL", "The address could not be parsed cleanly."),
        }
        url_rows = []
        for signal in url_details[0].get("signals", []):
            normalized = str(signal).lower().replace(" ", "_").replace("-", "_")
            title, meaning = url_labels.get(
                normalized,
                (fmt_category(signal), "Reported by the URL analyzer's lexical checks."),
            )
            url_rows.append({"Indicator": title, "Why it matters": meaning})
        if url_rows:
            st.dataframe(url_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No individual URL indicators were reported.")
        st.caption("URL inspection is lexical only; FraudLens does not visit or fetch the destination.")

    category_guidance = {
        "banking_kyc": "Contact your bank using the number on your official card or website. Do not use contact details supplied in the message.",
        "upi_payment": "Never enter a UPI PIN to receive money. A UPI PIN authorizes a payment.",
        "phishing": "Do not enter credentials after following a message link. Open the service independently using its official app or website.",
        "fake_job": "Verify the employer independently. Do not pay recruitment, registration or equipment fees to secure a job.",
        "romance": "Do not send money, gift cards or financial details to someone you have not independently verified.",
    }
    category_advice = category_guidance.get(str(entry.get("category", "")).lower())
    if category_advice:
        st.markdown(
            f'<div class="panel"><b>Category-specific safety advice</b><br>{html.escape(category_advice)}</div>',
            unsafe_allow_html=True,
        )

    with st.expander("Analyzer breakdown by modality"):
        if not entry["details"]:
            st.info("No analyzer details available.")
        for detail in entry["details"]:
            st.markdown(
                f"**{detail['source'].upper()}** — "
                f"{detail['score']:.2f} — {fmt_category(detail['category'])}"
            )
            st.caption(detail["explanation"])
            if detail["signals"]:
                st.write("Signals:", ", ".join(detail["signals"]))

    # Keep PDF report creation self-contained and optional.
    try:
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=38, leftMargin=38)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("FRAUDLENS", styles["Title"]),
            Paragraph("Threat Analysis Report", styles["Heading2"]),
            Spacer(1, 14),
        ]
        rows = [
            ["Timestamp", entry["time"]],
            ["Input type", entry["input_type"]],
            ["Risk indicator", f"{entry['score']:.2f} / 1.00"],
            ["Recommendation", status],
            ["Category", fmt_category(entry["category"])],
        ]
        table = Table(rows, colWidths=[125, 350])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EFF8")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
        story += [Spacer(1, 12), Paragraph("Explanation", styles["Heading2"]),
                  Paragraph(html.escape(entry["explanation"]), styles["BodyText"]),
                  Paragraph("Detected signals", styles["Heading2"])]
        for signal in entry["signals"] or ["No signals reported"]:
            story.append(Paragraph("• " + html.escape(signal), styles["BodyText"]))
        story.append(Paragraph("Detected tactics", styles["Heading2"]))
        story.append(Paragraph(
            html.escape(", ".join(entry["tactics"]) or "None reported"),
            styles["BodyText"]
        ))
        story.append(Spacer(1, 12))
        story.append(Paragraph(
            "Disclaimer: This heuristic risk indicator is not a calibrated probability "
            "and does not guarantee that an item is safe or fraudulent.",
            styles["Italic"],
        ))
        doc.build(story)
        buffer.seek(0)
        st.download_button(
            "⬇️ Download PDF Assessment Report",
            data=buffer.getvalue(),
            file_name="FraudLens_Assessment_Report.pdf",
            mime="application/pdf",
            key=f"pdf_{key_suffix}",
        )
    except ImportError:
        st.caption("Install reportlab to enable PDF reports: pip install reportlab")


    st.markdown("#### 🗳️ Was this assessment useful?")
    previous_feedback = entry.get("feedback")
    if previous_feedback:
        st.caption(f"Feedback recorded for this session: **{previous_feedback}**")
    feedback_cols = st.columns(3)
    for col, label, value in zip(
        feedback_cols,
        ["👍 Correct", "👎 Incorrect", "🤔 Not sure"],
        ["Correct", "Incorrect", "Unsure"],
    ):
        with col:
            if st.button(label, key=f"feedback_{key_suffix}_{value}"):
                entry["feedback"] = value
                st.session_state.feedback_log.append({
                    "time": entry["time"],
                    "input_type": entry["input_type"],
                    "category": entry["category"],
                    "decision": entry["recommendation"],
                    "feedback": value,
                })
                st.rerun()


def run_analysis(input_type, text_value="", messages=None, url_value="", image_bytes=None):
    results, errors = [], []

    if input_type in ("Text", "Multimodal") and text_value.strip():
        _run("text", analyze_text, text_value, results, errors)

    if input_type in ("Conversation", "Multimodal") and messages:
        _run("conversation", analyze_conversation, messages, results, errors)

    if input_type in ("URL", "Multimodal") and url_value.strip():
        _run("url", analyze_url, url_value, results, errors)

    if input_type in ("Screenshot", "Multimodal") and image_bytes:
        if len(image_bytes) > MAX_IMAGE_BYTES:
            st.error("Screenshot exceeds the 5 MB upload limit.")
            return
        _run("screenshot", analyze_screenshot, image_bytes, results, errors)

    if not results and not errors:
        st.warning("Provide input for this analysis mode before running analysis.")
        return

    verdict = fuse(results, errors)
    source_label = input_type
    add_to_history(verdict, source_label, text_value)

    for failed in errors:
        st.warning(
            f"The {failed} analyzer failed or could not read its input. "
            "It was excluded from the fused score."
        )

    st.success("Analysis completed.")


def execute_demo(label, sample):
    """Run a selected Overview scenario before Streamlit redraws the page."""
    st.session_state.demo_last_label = label
    st.session_state.demo_run_error = None
    try:
        run_analysis("Text", text_value=sample)
    except Exception as exc:
        st.session_state.demo_run_error = f"{type(exc).__name__}: {exc}"


# -------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -------------------------------------------------------------------

with st.sidebar:
    st.markdown("""
<div style="padding:12px 0 18px;">
    <div style="
        display:flex;
        align-items:center;
        gap:10px;
        white-space:nowrap;
    ">
        <span style="font-size:30px;">🛡️</span>
        <span style="
            font-size:27px;
            font-weight:900;
            letter-spacing:2px;
            color:#22D3EE;
        ">FRAUDLENS</span>
    </div>
    <div style="
        font-size:10px;
        font-weight:600;
        letter-spacing:2px;
        color:#94A3B8;
        margin-left:43px;
        margin-top:3px;
    ">CYBER THREAT INTELLIGENCE</div>
</div>
""", unsafe_allow_html=True)

    page = st.radio(
        "NAVIGATION",
        ["🏠 Overview", "🛡️ Threat Analysis", "📊 Analytics", "📜 Analysis History", "⚙️ Settings / About"],
        label_visibility="visible",
    )
    page = {
    "🏠 Overview": "Overview",
    "🛡️ Threat Analysis": "Threat Analysis",
    "📊 Analytics": "Analytics",
    "📜 Analysis History": "Analysis History",
    "⚙️ Settings / About": "Settings / About",
}.get(page, page)

    st.markdown("---")
    st.caption("SYSTEM TELEMETRY")
    st.write("🟢 Local analysis interface")
    st.write("🖼️ OCR engine: configured by vision module")
    st.write(f"📁 Session scans: {len(st.session_state.history)}")
    st.markdown("---")
    st.caption("FraudLens Major Project | Multimodal Scam Detection")


# -------------------------------------------------------------------
# OVERVIEW
# -------------------------------------------------------------------

if page == "Overview":
    st.markdown("""
    <div class="hero">
      <div class="hero-title">FraudLens Security Command Center</div>
      <div class="hero-sub">Multimodal cyber threat monitoring, scam pattern classification,
      and empirical risk assessment.</div>
    </div>
    """, unsafe_allow_html=True)

    dataset = load_eval_dataset()
    eval_obj = load_eval_results()
    session = st.session_state.history

    total_benchmark = len(dataset)
    scam_count = sum(1 for row in dataset if row.get("label") != "legitimate")
    legit_count = sum(1 for row in dataset if row.get("label") == "legitimate")

    integrated = {}
    if eval_obj:
        integrated = eval_obj.get("results", {}).get(
            "integrated (warn or block = scam)", {}
        )

    high_predictions = 0
    if integrated:
        high_predictions = integrated.get("tp", 0) + integrated.get("fp", 0)

    # Compact KPI strip styled to match the reference dashboard.
    live_total = len(session)
    live_threats = sum(1 for item in session if item["recommendation"] in ("warn", "block"))
    live_blocks = sum(1 for item in session if item["recommendation"] == "block")
    live_safe = sum(1 for item in session if item["recommendation"] == "safe")
    predicted_scams = high_predictions if integrated else scam_count

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card("TOTAL SCANS PERFORMED", f"{total_benchmark + live_total}",
                    f"{live_total} live + {total_benchmark} benchmark")
    with k2:
        metric_card("THREATS FLAGGED", f"{scam_count + live_threats}",
                    f"{live_threats} live + {scam_count} benchmark scam labels")
    with k3:
        metric_card("HIGH-RISK / BLOCKED", f"{predicted_scams + live_blocks}",
                    "Benchmark model predictions + live BLOCK decisions")
    with k4:
        metric_card("LEGITIMATE VERIFIED", f"{legit_count + live_safe}",
                    f"{live_safe} live SAFE + {legit_count} benchmark legitimate labels")

    st.markdown("---")
    left, right = st.columns(2)

    with left:
        st.subheader("📊 Threat Distribution by Scam Category")
        if session:
            # Live view: categories reported by actual analyzer runs.
            category_counts = {}
            for item in session:
                raw_label = str(item.get("category") or "unknown").lower()
                label = "legitimate_notification" if raw_label == "legitimate" else raw_label
                category_counts[label] = category_counts.get(label, 0) + 1
            chart_title = "Live session detections"
        elif dataset:
            # Initial view: benchmark distribution, including legitimate examples.
            category_counts = {}
            category_aliases = {
                "banking_kyc": "banking_kyc",
                "upi_payment": "upi_payment",
                "phishing": "phishing",
                "fake_job": "fake_job_offer",
                "romance": "romance_impersonation",
                "legitimate": "legitimate_notification",
            }
            for row in dataset:
                raw_label = str(row.get("category") or row.get("label") or "unknown").lower()
                label = category_aliases.get(raw_label, raw_label)
                category_counts[label] = category_counts.get(label, 0) + 1
            chart_title = "Benchmark dataset"
        else:
            category_counts = {}
            chart_title = "Threat categories"
        if category_counts:
            category_display = {
                "banking_kyc": "Banking / KYC",
                "upi_payment": "UPI / Payment",
                "phishing": "Phishing",
                "fake_job_offer": "Fake Job Offer",
                "romance_impersonation": "Romance / Impersonation",
                "legitimate_notification": "Legitimate Notification",
            }
            display_names = [category_display.get(k, fmt_category(k)) for k in category_counts]
            fig = px.pie(
                names=display_names,
                values=list(category_counts.values()),
                hole=0.58,
                template="plotly_dark",
            )
            fig.update_traces(textposition="inside", textinfo="percent")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend_title_text="",
                margin=dict(t=5, b=5, l=5, r=5),
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Category chart unavailable. Check data/eval_set.jsonl.")

    with right:
        st.subheader("⚡ Risk Severity Classification Breakdown")
        if session:
            severity = {"Low (0–39)": 0, "Medium (40–69)": 0,
                        "High (70–84)": 0, "Critical (85–100)": 0}
            for item in session:
                score = item["score"] * 100
                if score < 40:
                    severity["Low (0–39)"] += 1
                elif score < 70:
                    severity["Medium (40–69)"] += 1
                elif score < 85:
                    severity["High (70–84)"] += 1
                else:
                    severity["Critical (85–100)"] += 1
            fig = px.bar(
                x=list(severity.keys()), y=list(severity.values()),
                labels={"x": "Severity", "y": "Session analyses"},
                template="plotly_dark",
                color=list(severity.keys()),
            )
            fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Difficulty is the benchmark's available severity proxy before live scans.
            severity = {"Critical (85–100)": 0, "High (70–84)": 0,
                        "Medium (40–69)": 0, "Low (0–39)": 0}
            difficulty_map = {
                "critical": "Critical (85–100)", "hard": "High (70–84)",
                "high": "High (70–84)", "medium": "Medium (40–69)",
                "easy": "Low (0–39)", "low": "Low (0–39)",
            }
            for row in dataset:
                difficulty = str(row.get("difficulty", "")).lower()
                bucket = difficulty_map.get(difficulty)
                if bucket:
                    severity[bucket] += 1
            fig = px.bar(
                x=list(severity.keys()), y=list(severity.values()),
                labels={"x": "Severity", "y": "Benchmark examples"},
                template="plotly_dark",
                color=list(severity.keys()),
                color_discrete_map={
                    "Critical (85–100)": "#ef4444",
                    "High (70–84)": "#f97316",
                    "Medium (40–69)": "#eab308",
                    "Low (0–39)": "#10b981",
                },
            )
            fig.update_layout(
                showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", height=300,
                margin=dict(t=5, b=5, l=5, r=5),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("After a quick demo, this chart switches to live risk-score severity.")

    st.markdown("---")
    st.subheader("🚀 Review & Viva Quick Demonstration Scenarios")
    st.caption(
        "Select a scenario to run it through FraudLens. The assessment appears below, "
        "and the category and severity charts update to reflect the live result."
    )
    demos = {
        "🚨 Fake Bank KYC Block": (
            "Your bank account will be blocked today. Complete KYC immediately "
            "and share your OTP to avoid suspension."
        ),
        "💼 Advance-Fee Job Scam": (
            "Congratulations! You are selected for a work-from-home job. "
            "Pay a registration fee immediately to confirm your position."
        ),
        "💸 Fake UPI Cashback": (
            "You have won a cashback reward. Scan this QR code and enter your "
            "UPI PIN to receive the money."
        ),
        "✅ Genuine Bank Debit Alert": (
            "Your account was debited Rs. 500. If you did not make this transaction, "
            "contact your bank using the official number. Never share your OTP or PIN."
        ),
    }
    cols = st.columns(4)
    for idx, (label, sample) in enumerate(demos.items()):
        with cols[idx]:
            st.button(
                label,
                key=f"demo_{idx}",
                use_container_width=True,
                on_click=execute_demo,
                args=(label, sample),
            )

    if st.session_state.get("demo_run_error"):
        st.error(
            "The demonstration could not complete. Check the analyzer setup and "
            f"terminal traceback. Details: {st.session_state.demo_run_error}"
        )

    # Callback stores the result before this page is redrawn, so it appears reliably.
    if (
        st.session_state.latest
        and st.session_state.get("demo_last_label")
        and not st.session_state.get("demo_run_error")
    ):
        st.markdown("---")
        st.markdown(f"### 🛡️ Threat Intelligence Assessment")
        st.caption(f"Scenario executed: {st.session_state.demo_last_label}")
        show_verdict(st.session_state.latest, key_suffix="overview_demo")

    st.markdown("---")
    st.subheader("Current Session Activity")
    if session:
        st.dataframe(
            [{
                "Time": x["time"], "Input": x["input_type"],
                "Risk": f"{x['score'] * 100:.0f}/100",
                "Decision": x["recommendation"].upper(),
                "Category": fmt_category(x["category"]),
            } for x in session[:8]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No session analyses yet.")


# -------------------------------------------------------------------
# THREAT ANALYSIS - DISTINCT MODE TABS
# -------------------------------------------------------------------

elif page == "Threat Analysis":
    st.title("Threat Analysis & Intelligence Engine")
    st.caption(
        "Inspect suspicious messages, chat histories, phishing URLs, and screenshots "
        "using specialized modules."
    )

    st.info(
        "Use this page to test your own examples. Every result below—including the charts—"
        "is generated from the input submitted in the selected tab."
    )

    mode_tabs = st.tabs([
        "💬 Text Analysis",
        "🗨️ Conversation Analysis",
        "🔗 URL Phishing Inspector",
        "🖼️ Screenshot Analysis",
        "🧩 Multimodal Fusion",
    ])

    with mode_tabs[0]:
        st.subheader("Analyze a Single Message")
        text_value = st.text_area(
            "SMS, email or WhatsApp message",
            height=170, max_chars=10000, key="single_text",
        )
        c1, c2 = st.columns([1, 5])
        with c1:
            run_text = st.button("Analyze Text", key="run_text")
        with c2:
            st.caption("The text analyzer evaluates message content and reports evidence.")
        if run_text:
            run_analysis("Text", text_value=text_value)
        if st.session_state.latest and st.session_state.latest["input_type"] == "Text":
            show_verdict(st.session_state.latest, "text_tab")

    with mode_tabs[1]:
        st.subheader("Analyze a Multi-Turn Conversation")
        st.caption("Enter one message per line, oldest message first.")
        convo = st.text_area(
            "Conversation history", height=210, max_chars=10000, key="single_conversation"
        )
        if st.button("Analyze Conversation", key="run_conversation"):
            messages = [m.strip() for m in convo.splitlines() if m.strip()]
            run_analysis("Conversation", messages=messages)
        if st.session_state.latest and st.session_state.latest["input_type"] == "Conversation":
            show_verdict(st.session_state.latest, "conversation_tab")

    with mode_tabs[2]:
        st.subheader("Inspect a Suspicious URL")
        st.warning("FraudLens inspects URL text only. It does not open or fetch the destination.")
        url_value = st.text_input("Enter URL", max_chars=2048, key="single_url")
        if st.button("Inspect URL", key="run_url"):
            run_analysis("URL", url_value=url_value)
        if st.session_state.latest and st.session_state.latest["input_type"] == "URL":
            show_verdict(st.session_state.latest, "url_tab")

    with mode_tabs[3]:
        st.subheader("Analyze a Screenshot")
        st.caption("PNG/JPG/JPEG, maximum 5 MB. OCR and image inspection are handled by the existing vision module.")
        uploaded = st.file_uploader(
            "Upload suspicious screenshot",
            type=["png", "jpg", "jpeg"],
            key="single_screenshot",
        )
        if uploaded:
            st.image(uploaded, caption="Screenshot preview", use_container_width=True)
        if st.button("Analyze Screenshot", key="run_screenshot"):
            if uploaded is None:
                st.warning("Upload a screenshot first.")
            else:
                run_analysis("Screenshot", image_bytes=uploaded.getvalue())
        if st.session_state.latest and st.session_state.latest["input_type"] == "Screenshot":
            show_verdict(st.session_state.latest, "screenshot_tab")

    with mode_tabs[4]:
        st.subheader("Multimodal Fusion Analysis")
        st.caption("Provide any combination of text, conversation, URL and screenshot. "
                   "All available analyzer outputs are combined by the existing fusion engine.")
        multi_text = st.text_area("Message text", height=110, key="multi_text")
        multi_convo = st.text_area(
            "Conversation (one message per line)", height=110, key="multi_conversation"
        )
        multi_url = st.text_input("URL", key="multi_url", max_chars=2048)
        multi_image = st.file_uploader(
            "Screenshot (PNG/JPG, max 5 MB)",
            type=["png", "jpg", "jpeg"],
            key="multi_screenshot",
        )
        if multi_image:
            st.image(multi_image, caption="Multimodal screenshot input", width=300)

        if st.button("Run Multimodal Fusion", key="run_multimodal"):
            messages = [m.strip() for m in multi_convo.splitlines() if m.strip()]
            image_bytes = multi_image.getvalue() if multi_image else None
            run_analysis(
                "Multimodal",
                text_value=multi_text,
                messages=messages,
                url_value=multi_url,
                image_bytes=image_bytes,
            )
        if st.session_state.latest and st.session_state.latest["input_type"] == "Multimodal":
            show_verdict(st.session_state.latest, "multimodal_tab")

    # Highlight the latest text evidence only where it belongs.
    latest = st.session_state.latest
    if latest and latest.get("original_text"):
        with st.expander("View highlighted text evidence"):
            st.markdown(
                '<div class="panel" style="line-height:2;">'
                + highlight_evidence(latest["original_text"], latest["signals"])
                + "</div>",
                unsafe_allow_html=True,
            )
            st.caption("Only analyzer-reported signal phrases that match the text are highlighted.")


# -------------------------------------------------------------------
# ANALYTICS - GRAPHS + CONFUSION MATRIX + METRICS TABLE
# -------------------------------------------------------------------

elif page == "Analytics":
    st.title("Forensic Analytics & Model Benchmarks")
    st.caption(
        "Evaluation metrics are calculated on the labeled evaluation dataset. "
        "They are not live usage statistics or guarantees of real-world accuracy."
    )

    eval_obj = load_eval_results()
    if not eval_obj:
        st.warning("No saved evaluation results found. Run: python -m system.evaluate")
    else:
        results = eval_obj.get("results", {})
        st.caption(
            f"Dataset: {eval_obj.get('dataset', 'Unknown')} · "
            f"Samples: {eval_obj.get('n_examples', 'Unknown')} · "
            f"Run time: {eval_obj.get('run_time', 'Unknown')}"
        )

        # Use the actual approach names from system/evaluate.py.
        display_map = [
            ("keyword_baseline", "Keyword Baseline"),
            ("url_only", "URL Only"),
            ("text_keywords_only", "Text Keywords Only"),
            ("text_only", "Text NLP"),
            ("integrated (warn or block = scam)", "Multimodal Integrated"),
        ]
        available = [(key, label) for key, label in display_map if key in results]

        if not available:
            st.warning("The saved evaluation JSON does not contain the expected approaches.")
        else:
            integrated_key = "integrated (warn or block = scam)"
            primary = results.get(integrated_key, results[available[-1][0]])

            # Summary cards follow the integrated approach if present.
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                metric_card("Multimodal accuracy", f"{primary.get('accuracy', 0)*100:.1f}%",
                            "Dataset classification accuracy")
            with k2:
                metric_card("Precision", f"{primary.get('precision', 0)*100:.1f}%",
                            "Positive predictive value")
            with k3:
                metric_card("Recall", f"{primary.get('recall', 0)*100:.1f}%",
                            "Scam samples identified")
            with k4:
                metric_card("F1 score", f"{primary.get('f1', 0):.3f}",
                            "Harmonic mean of precision and recall")

            st.markdown("---")
            st.subheader("📈 Cross-Modality Performance Comparison")
            metric_names = ["Accuracy", "Precision", "Recall", "F1 Score"]
            fig = go.Figure()
            for metric, field in zip(metric_names, ["accuracy", "precision", "recall", "f1"]):
                fig.add_trace(go.Bar(
                    name=metric,
                    x=[label for _, label in available],
                    y=[results[key].get(field, 0) for key, _ in available],
                ))
            fig.update_layout(
                barmode="group", template="plotly_dark",
                yaxis=dict(title="Metric value", range=[0, 1]),
                xaxis_title="Evaluation approach",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend_title="Metric",
                margin=dict(t=25, b=80),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            left, right = st.columns([1, 1.35])

            with left:
                st.subheader("🎯 Multimodal Confusion Matrix")
                tn = primary.get("tn", 0)
                fp = primary.get("fp", 0)
                fn = primary.get("fn", 0)
                tp = primary.get("tp", 0)
                matrix = [[tn, fp], [fn, tp]]
                cm = go.Figure(data=go.Heatmap(
                    z=matrix,
                    x=["Predicted Legitimate", "Predicted Scam"],
                    y=["Actual Legitimate", "Actual Scam"],
                    text=[[f"TN: {tn}", f"FP: {fp}"],
                          [f"FN: {fn}", f"TP: {tp}"]],
                    texttemplate="%{text}",
                    colorscale="Blues",
                    showscale=False,
                ))
                cm.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=15, b=15),
                )
                st.plotly_chart(cm, use_container_width=True)

            with right:
                st.subheader("📋 Detailed Metrics Table")
                rows = []
                for key, label in available:
                    m = results[key]
                    rows.append({
                        "Approach": label,
                        "Accuracy": f"{m.get('accuracy', 0)*100:.1f}%",
                        "Precision": f"{m.get('precision', 0)*100:.1f}%",
                        "Recall": f"{m.get('recall', 0)*100:.1f}%",
                        "F1 Score": f"{m.get('f1', 0):.3f}",
                        "TP": m.get("tp", 0),
                        "FP": m.get("fp", 0),
                        "TN": m.get("tn", 0),
                        "FN": m.get("fn", 0),
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Inspect an Evaluation Approach")
            selected_key = st.selectbox(
                "Choose approach",
                [key for key, _ in available],
                format_func=lambda k: dict(available)[k],
            )
            selected_metrics = results[selected_key]
            st.write(
                f"**False positive rate:** {selected_metrics.get('false_positive_rate', 0):.3f} · "
                f"**Failed examples:** {selected_metrics.get('failed_examples', 0)}"
            )
            misclassified = selected_metrics.get("errors", [])
            if misclassified:
                st.dataframe(misclassified, use_container_width=True, hide_index=True)
            else:
                st.success("No misclassified examples were recorded for this approach.")

            st.info(
                "Interpretation: TP = scam correctly flagged; TN = legitimate correctly "
                "identified; FP = legitimate incorrectly flagged; FN = scam missed. "
                "The dataset is synthetic and limited, so report these as prototype "
                "evaluation results only."
            )


# -------------------------------------------------------------------
# ANALYSIS HISTORY
# -------------------------------------------------------------------

elif page == "Analysis History":
    st.title("Session Threat Analysis Log")
    history = st.session_state.history

    if not history:
        st.info("No analysis has been performed in this session yet.")
    else:
        st.subheader("📈 Session Threat Trends")
        decision_counts = {}
        category_counts = {}
        for item in history:
            decision = str(item["recommendation"]).upper()
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
            category = fmt_category(item.get("category"))
            category_counts[category] = category_counts.get(category, 0) + 1

        trend_left, trend_right = st.columns(2)
        with trend_left:
            decision_fig = px.pie(
                names=list(decision_counts.keys()),
                values=list(decision_counts.values()),
                hole=0.55,
                title="SAFE / WARN / BLOCK distribution",
                template="plotly_dark",
            )
            decision_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=280)
            st.plotly_chart(decision_fig, use_container_width=True)
        with trend_right:
            category_fig = px.bar(
                x=list(category_counts.keys()),
                y=list(category_counts.values()),
                title="Scans by detected category",
                template="plotly_dark",
            )
            category_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=280,
                xaxis_title="Category",
                yaxis_title="Number of scans",
            )
            st.plotly_chart(category_fig, use_container_width=True)

        import pandas as pd
        csv_data = pd.DataFrame([{
            "Timestamp": item["time"],
            "Input type": item["input_type"],
            "Risk score": item["score"],
            "Decision": item["recommendation"],
            "Category": item["category"],
            "Feedback": item.get("feedback", ""),
        } for item in history]).to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Export session history (CSV)",
            data=csv_data,
            file_name="FraudLens_Session_History.csv",
            mime="text/csv",
            key="export_session_history",
        )

        st.dataframe(
            [{
                "Timestamp": item["time"],
                "Input": item["input_type"],
                "Risk": f"{item['score']*100:.0f}/100",
                "Decision": item["recommendation"].upper(),
                "Category": fmt_category(item["category"]),
            } for item in history],
            use_container_width=True,
            hide_index=True,
        )
        if st.session_state.feedback_log:
            st.subheader("🗳️ Tester Feedback Summary")
            feedback_counts = {}
            for item in st.session_state.feedback_log:
                feedback_counts[item["feedback"]] = feedback_counts.get(item["feedback"], 0) + 1
            feedback_fig = px.bar(
                x=list(feedback_counts.keys()),
                y=list(feedback_counts.values()),
                labels={"x": "Feedback", "y": "Responses"},
                template="plotly_dark",
            )
            feedback_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(feedback_fig, use_container_width=True)

        selected = st.selectbox(
            "Inspect a previous report",
            range(len(history)),
            format_func=lambda i: (
                f"{history[i]['time']} | {history[i]['input_type']} | "
                f"{history[i]['recommendation'].upper()}"
            ),
        )
        show_verdict(history[selected], key_suffix=f"history_{selected}")
        if st.button("Clear session history"):
            st.session_state.history = []
            st.session_state.latest = None
            st.rerun()


# -------------------------------------------------------------------
# SETTINGS / ABOUT
# -------------------------------------------------------------------

elif page == "Settings / About":

    st.html("""
    <div style="
        background:linear-gradient(120deg,#101c32,#172d4c);
        border:1px solid #284568;
        border-radius:16px;
        padding:28px;
        margin-bottom:24px;">
        <div style="font-size:13px;color:#22d3ee;
                    letter-spacing:3px;font-weight:700;">
            PROJECT INFORMATION CENTER
        </div>
        <h1 style="color:white;font-size:38px;margin:12px 0 5px 0;">
            🛡️ FraudLens
        </h1>
        <h3 style="color:#22d3ee;font-weight:500;">
            Multimodal AI-Powered Scam Detection
        </h3>
        <p style="color:#cbd5e1;font-size:15px;line-height:1.8;">
            An intelligent scam detection platform designed to
            analyze suspicious messages, conversations, URLs and
            screenshots. FraudLens combines specialized analysis
            modules to generate risk assessments, explain detected
            indicators and provide safety recommendations.
        </p>
    </div>
    """)


    # PROJECT PURPOSE
    st.subheader("🎯 Project Purpose")

    st.write(
        "FraudLens aims to help users identify potentially fraudulent "
        "digital communications before they become victims of scams. "
        "Instead of relying on a single detection method, the system "
        "uses multiple specialized analyzers and combines their results."
    )

    # CORE MODULES
    st.subheader("🧠 Core Intelligence Modules")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("""
        <div class="panel">
        <h3 style="color:#22d3ee;">💬 NLP Analysis</h3>
        Identifies suspicious words, urgency, manipulation tactics,
        credential requests and common scam patterns in messages
        and conversations.
        </div>

        <div class="panel">
        <h3 style="color:#f59e0b;">🔗 URL Intelligence</h3>
        Examines URL characteristics such as HTTPS usage,
        suspicious domain extensions, IP-based hosts, shorteners,
        punycode and possible brand impersonation.
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="panel">
        <h3 style="color:#a78bfa;">🖼️ Vision Analysis</h3>
        Extracts text from screenshots using OCR and performs
        image-quality and QR-code inspection.
        </div>

        <div class="panel">
        <h3 style="color:#34d399;">⚙️ Fusion Engine</h3>
        Combines usable analyzer outputs using weighted scoring
        to generate a final risk score, recommendation and
        supporting explanation.
        </div>
        """, unsafe_allow_html=True)

    # SYSTEM WORKFLOW
    st.markdown("---")
    st.subheader("🔄 How FraudLens Works")

    steps = [
        ("01", "Input Collection",
         "Text, conversations, URLs and screenshots"),
        ("02", "Specialized Analysis",
         "NLP, OCR, vision and URL inspection"),
        ("03", "Risk Fusion",
         "Combines usable analyzer results"),
        ("04", "Threat Assessment",
         "SAFE, WARN or BLOCK recommendation"),
        ("05", "Explainable Output",
         "Risk score, evidence and safety advice"),
    ]

    for number, heading, description in steps:
        with st.container(border=True):
            a, b = st.columns([1, 5])
            with a:
                st.markdown(
                    f"<h2 style='color:#22d3ee;'>{number}</h2>",
                    unsafe_allow_html=True
                )
            with b:
                st.markdown(f"**{heading}**")
                st.caption(description)

    # RISK SCORING
    st.markdown("---")
    st.subheader("📊 Risk Scoring Methodology")

    st.write(
        "FraudLens combines the maximum analyzer score and the "
        "mean analyzer score to calculate the final risk indicator."
    )

    st.latex(
        r"Risk = 0.60 \\times Max(Scores) "
        r"+ 0.40 \\times Mean(Scores)"
    )

    x1, x2, x3 = st.columns(3)

    with x1:
        st.metric("SAFE", "< 0.40")
        st.caption("Lower risk indicator")

    with x2:
        st.metric("WARN", "0.40 – 0.69")
        st.caption("Suspicious activity")

    with x3:
        st.metric("BLOCK", "≥ 0.70")
        st.caption("High risk indicator")

    # SCAM CATEGORIES
    st.markdown("---")
    st.subheader("🚨 Supported Scam Categories")

    categories = [
        ("🏦", "Banking / KYC"),
        ("💳", "UPI / Payment Fraud"),
        ("🌐", "Phishing"),
        ("💼", "Fake Job Offers"),
        ("❤️", "Romance Scams"),
        ("✅", "Legitimate Communications"),
    ]

    category_cols = st.columns(3)

    for i, (emoji, category) in enumerate(categories):
        with category_cols[i % 3]:
            st.markdown(
                f"""
                <div class="panel" style="text-align:center;
                     min-height:90px;">
                    <div style="font-size:25px;">{emoji}</div>
                    <b>{category}</b>
                </div>
                """,
                unsafe_allow_html=True
            )

    # TECHNOLOGY STACK
    st.markdown("---")
    st.subheader("💻 Technology Stack")

    technologies = [
        ("Python", "Core programming language"),
        ("Streamlit", "Interactive dashboard"),
        ("NLP", "Text and conversation analysis"),
        ("OpenCV", "Image processing"),
        ("Tesseract OCR", "Text extraction from screenshots"),
        ("Plotly", "Interactive visualizations"),
        ("Pytest", "Software testing"),
    ]

    for technology, purpose in technologies:
        st.markdown(
            f"**{technology}**  \n"
            f"<span style='color:#94a3b8;'>{purpose}</span>",
            unsafe_allow_html=True
        )

    # PROJECT CONTRIBUTION

    st.markdown("---")
    st.subheader("🎓 Academic Project Contribution")

    st.html("""
    <div style="
        background:linear-gradient(120deg,#101c32,#172d4c);
        border:1px solid #284568;
        border-radius:16px;
        padding:24px;
        margin-bottom:20px;">

        <h3 style="color:#22d3ee;">Our Objective</h3>

        <p style="color:#cbd5e1;line-height:1.8;">
            To develop an explainable multimodal scam detection
            prototype that brings different detection techniques
            together into one platform.
        </p>

        <br>

        <h4 style="color:white;">Key Contributions</h4>

        <ul style="color:#cbd5e1;line-height:2;">
            <li>Multiple input-based scam analysis.</li>
            <li>Specialized NLP, vision and URL analysis.</li>
            <li>Weighted risk fusion and threat classification.</li>
            <li>Explainable evidence and safety recommendations.</li>
            <li>Dataset-based model evaluation and performance analysis.</li>
        </ul>

    </div>
    """)


    # DISCLAIMER
    st.markdown("---")
    st.warning(
        "FraudLens is an academic scam-detection prototype. "
        "Its risk scores are heuristic indicators, not calibrated "
        "probabilities. A SAFE result does not guarantee that a "
        "message or URL is legitimate."
    )

    st.markdown("""
    <div style="text-align:center;padding:20px;">
        <h2 style="color:#22d3ee;">🛡️ FRAUDLENS</h2>
        <p style="color:#94a3b8;">
            Multimodal AI-Powered Scam Detection<br>
            Major Project | Computer Science & Engineering
        </p>
        <p style="color:#64748b;font-size:12px;">
            Designed to promote safer digital communication.
        </p>
    </div>
    """, unsafe_allow_html=True)
