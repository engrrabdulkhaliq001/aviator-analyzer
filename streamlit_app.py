"""Aviator M6 Streamlit Cloud frontend; inference stays on the VM."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

from app.input_validation import parse_rounds_text

load_dotenv()

try:
    secret_backend_url = st.secrets.get("BACKEND_API_URL", "")
except Exception:
    secret_backend_url = ""

BACKEND_API_URL = (
    os.getenv("BACKEND_API_URL")
    or secret_backend_url
    or "https://aviator-m6.duckdns.org"
).rstrip("/")

st.set_page_config(
    page_title="Aviator M6 | Experimental Analytics",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

        :root {
            --m6-bg: #0b1220;
            --m6-panel: #111827;
            --m6-panel-soft: #172033;
            --m6-border: #26344a;
            --m6-text: #f4f7fb;
            --m6-muted: #9aa8bb;
            --m6-accent: #6366f1;
            --m6-accent-soft: rgba(99, 102, 241, .14);
            --m6-green: #34d399;
            --m6-amber: #fbbf24;
            --m6-red: #f87171;
        }

        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background: var(--m6-bg) !important;
            color: var(--m6-text) !important;
            font-family: 'DM Sans', sans-serif !important;
        }

        [data-testid="stHeader"] { background: transparent !important; }
        .block-container { max-width: 760px; padding: 3rem 1.25rem 2rem; }
        h1, h2, h3 { letter-spacing: 0 !important; }
        h1 { font-size: clamp(2rem, 6vw, 3.2rem) !important; line-height: 1.05 !important; }
        h2 { font-size: 1.35rem !important; }
        h3 { font-size: 1.05rem !important; }

        .m6-eyebrow {
            color: #a5b4fc;
            font: 700 .72rem 'Space Mono', monospace;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: .65rem;
        }
        .m6-subtitle { color: var(--m6-muted); font-size: 1rem; line-height: 1.6; max-width: 560px; }
        .m6-status { color: var(--m6-muted); font-size: .84rem; margin: 1.1rem 0 2.2rem; }
        .m6-status-dot { color: var(--m6-green); font-size: 1rem; vertical-align: -1px; }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--m6-panel) !important;
            border: 1px solid var(--m6-border) !important;
            border-radius: 10px !important;
        }
        div[data-testid="stTextInput"] input {
            background: var(--m6-panel-soft) !important;
            border: 1px solid var(--m6-border) !important;
            border-radius: 7px !important;
            color: var(--m6-text) !important;
            font: 700 1.15rem 'Space Mono', monospace !important;
            min-height: 3rem;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: var(--m6-accent) !important;
            box-shadow: 0 0 0 1px var(--m6-accent) !important;
        }
        label { color: var(--m6-muted) !important; }
        .stButton > button[kind="primary"] {
            background: var(--m6-accent) !important;
            border: 1px solid #818cf8 !important;
            border-radius: 7px !important;
            color: white !important;
            font-weight: 700 !important;
            min-height: 3rem;
        }
        .stButton > button[kind="primary"]:hover { background: #5558d9 !important; }
        .m6-section-label {
            color: var(--m6-muted);
            font-size: .75rem;
            font-weight: 700;
            letter-spacing: .04em;
            margin-bottom: .55rem;
            text-transform: uppercase;
        }
        .m6-result-title { margin-bottom: .1rem; }
        .m6-result-mode { color: var(--m6-muted); font-size: .92rem; margin-bottom: 1.1rem; }
        .m6-prob-card {
            background: var(--m6-panel-soft);
            border: 1px solid var(--m6-border);
            border-radius: 8px;
            min-height: 104px;
            padding: .85rem .75rem;
        }
        .m6-prob-label { color: var(--m6-muted); font-size: .74rem; line-height: 1.3; }
        .m6-prob-value { color: var(--m6-text); font: 700 1.55rem 'Space Mono', monospace; margin: .35rem 0 .5rem; }
        .m6-bar { background: #25324a; border-radius: 99px; height: 5px; overflow: hidden; }
        .m6-bar-fill { background: var(--m6-accent); border-radius: 99px; height: 100%; }
        .m6-ai-label { color: #a5b4fc; font-size: .78rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
        .m6-ai-copy { color: #d8deea; font-size: .94rem; line-height: 1.65; margin-top: .45rem; }
        .m6-history-row { border-bottom: 1px solid var(--m6-border); color: var(--m6-muted); padding: .65rem 0; }
        .m6-history-row:last-child { border-bottom: 0; }
        .m6-history-range { color: var(--m6-text); margin-left: .4rem; }
        .m6-disclaimer { color: #8290a5; font-size: .78rem; line-height: 1.55; margin-top: 2rem; }
        @media (max-width: 560px) {
            .block-container { padding-top: 2rem; }
            .m6-prob-card { min-height: 94px; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=10)
def fetch_backend_health() -> dict[str, Any]:
    try:
        response = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {"status": "offline", "model_status": "offline", "dataset_rows": 0}


def call_predict_api(rounds: list[float]) -> dict[str, Any] | None:
    try:
        response = requests.post(
            f"{BACKEND_API_URL}/predict",
            json={"recent_rounds": rounds, "include_ai_explanation": True},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
        try:
            detail = response.json().get("detail", "Request could not be processed.")
        except ValueError:
            detail = "Request could not be processed."
        if response.status_code == 422:
            st.error(f"Please check the round values: {detail}")
        elif 400 <= response.status_code < 500:
            st.error("The analysis request could not be accepted. Please check your values.")
        else:
            st.error("The analysis service is temporarily unavailable. Please try again.")
    except requests.exceptions.Timeout:
        st.error("The analysis service took too long to respond. Please try again.")
    except requests.RequestException:
        st.error("The analysis service is unavailable right now. Please try again later.")
    return None


def probability_card(label: str, value: float) -> str:
    percent = max(0.0, min(100.0, value * 100))
    return f"""
    <div class="m6-prob-card">
        <div class="m6-prob-label">{label}</div>
        <div class="m6-prob-value">{percent:.1f}%</div>
        <div class="m6-bar"><div class="m6-bar-fill" style="width:{percent:.1f}%"></div></div>
    </div>
    """


health = fetch_backend_health()
service_online = health.get("status") == "online"

st.markdown('<div class="m6-eyebrow">Aviator M6</div>', unsafe_allow_html=True)
st.title("Experimental Round Analyzer")
st.markdown(
    "Enter your recent round values to generate an experimental statistical analysis.",
    help="The M6 model runs privately on the VM. This page is only the user interface.",
)
st.markdown(
    f'<div class="m6-status"><span class="m6-status-dot">●</span> '
    f'{"Analysis service online" if service_online else "Analysis service unavailable"}</div>',
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown('<div class="m6-section-label">Recent round values</div>', unsafe_allow_html=True)
    first_round = st.text_input(
        "Round value",
        value="",
        placeholder="e.g. 1.24",
        label_visibility="collapsed",
        key="first_round",
    )
    second_round = st.text_input(
        "Optional second round",
        value="",
        placeholder="Optional second round, e.g. 1.67",
        label_visibility="visible",
        key="second_round",
    )
    analyze = st.button("Analyze", type="primary", use_container_width=True)

if analyze:
    raw_values = first_round if not second_round.strip() else f"{first_round},{second_round}"
    try:
        rounds = parse_rounds_text(raw_values)
        with st.spinner("Analyzing recent rounds..."):
            result = call_predict_api(rounds)
        if result and result.get("status") == "success":
            st.session_state["latest_result"] = result
            st.session_state.setdefault("history", []).insert(
                0,
                {
                    "time": datetime.now().strftime("%H:%M"),
                    "rounds": rounds,
                    "range": result["prediction"]["estimated_range"],
                },
            )
            st.session_state["history"] = st.session_state["history"][:5]
    except ValueError:
        st.error("Please enter a valid round value between 1.00 and 10,000.")

result = st.session_state.get("latest_result")
if result and result.get("status") == "success":
    prediction = result["prediction"]
    probabilities = result.get("probabilities", {})

    st.write("")
    with st.container(border=True):
        st.markdown('<div class="m6-section-label">Analysis result</div>', unsafe_allow_html=True)
        st.subheader(prediction.get("estimated_range", "Analysis complete"))
        st.markdown(
            f'<div class="m6-result-mode">{prediction.get("model_type", "analysis").replace("_", " ").title()} · '
            f'{prediction.get("confidence_level", "") } confidence</div>',
            unsafe_allow_html=True,
        )

        cards = [
            ("Low · under 1.50x", probabilities.get("under_1_50", 0.0)),
            ("Medium · 1.50x–2x", probabilities.get("1_50_to_2", 0.0)),
            ("High · 2x–5x", probabilities.get("2_to_5", 0.0)),
            ("Very high · 5x–10x", probabilities.get("5_to_10", 0.0)),
            ("10x+", probabilities.get("10_plus", 0.0)),
        ]
        columns = st.columns(5, gap="small")
        for column, (label, value) in zip(columns, cards):
            with column:
                st.markdown(probability_card(label, value), unsafe_allow_html=True)

        st.markdown('<div class="m6-ai-label" style="margin-top:1.3rem">What does this mean?</div>', unsafe_allow_html=True)
        explanation = result.get("ai_explanation") or "No additional explanation was returned."
        st.markdown(f'<div class="m6-ai-copy">{explanation}</div>', unsafe_allow_html=True)

    with st.expander("About this analysis"):
        st.write(
            "The result is generated by the private M6 model using the recent round values you entered. "
            "It is an experimental statistical estimate, not a prediction guarantee."
        )
        st.caption(
            f"Dataset rows: {prediction.get('dataset_rows', '—')} · "
            f"Backend: {BACKEND_API_URL} · "
            f"Processing: {result.get('processing_time_ms', 0):.0f} ms"
        )

history = st.session_state.get("history", [])
if history:
    with st.expander("Recent analyses"):
        for item in history:
            rounds = ", ".join(f"{value:g}x" for value in item["rounds"])
            st.markdown(
                f'<div class="m6-history-row">{item["time"]} · {rounds}'
                f'<span class="m6-history-range">{item["range"].split("(")[0].strip()}</span></div>',
                unsafe_allow_html=True,
            )

st.markdown(
    '<div class="m6-disclaimer">Experimental statistical estimates only. '
    'Results are not guaranteed and should not be treated as financial or betting advice.</div>',
    unsafe_allow_html=True,
)
