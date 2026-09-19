"""Aviator M6 Streamlit Cloud frontend; inference stays on the VM."""
from __future__ import annotations
import os
from datetime import datetime
from typing import Any
import requests
import streamlit as st
from app.input_validation import parse_rounds_text

try:
    secret_url = st.secrets.get("BACKEND_API_URL", "")
except Exception:
    secret_url = ""
BACKEND_API_URL = (os.getenv("BACKEND_API_URL") or secret_url or "https://aviator-m6.duckdns.org").rstrip("/")
st.set_page_config(page_title="Aviator M6 Analytics", page_icon="✈️", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap');
:root { --bg:#090d14; --panel:#111925; --line:#263447; --cyan:#48e0e8; --muted:#91a1b5; }
html, body, [data-testid="stAppViewContainer"] { background:var(--bg); color:#f4f7fb; font-family:'DM Sans',sans-serif; }
.block-container { max-width:1180px; padding-top:2rem; }
.hero { border:1px solid var(--line); background:linear-gradient(135deg,#101b2b,#0d131e); padding:1.6rem 1.8rem; border-radius:12px; margin-bottom:1rem; }
.kicker { color:var(--cyan); font-family:'Space Mono',monospace; font-size:.75rem; letter-spacing:.08em; }
.hero h1 { margin:.35rem 0; font-size:2.2rem; } .hero p,.muted { color:var(--muted); }
.panel { border:1px solid var(--line); background:var(--panel); padding:1.25rem; border-radius:10px; height:100%; }
.metric { background:#0d1521; border:1px solid var(--line); border-radius:8px; padding:.9rem; }
.metric strong { display:block; color:var(--cyan); font:700 1.35rem 'Space Mono',monospace; margin-top:.25rem; }
.disclaimer { border-top:1px solid var(--line); margin-top:1.5rem; padding-top:1rem; color:var(--muted); font-size:.82rem; }
</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=10)
def backend_health() -> dict[str, Any]:
    try:
        response = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        return {"status":"offline", "model_status":"offline", "error":str(exc)}

def call_prediction(rounds: list[float]) -> dict[str, Any] | None:
    try:
        response = requests.post(f"{BACKEND_API_URL}/predict", json={"recent_rounds":rounds, "include_ai_explanation":True}, timeout=30)
        if response.status_code != 200:
            try:
                detail = response.json().get("detail", "Request could not be processed.")
            except ValueError:
                detail = "Request could not be processed."
            st.error(f"Input validation error: {detail}" if response.status_code == 422 else f"Backend request failed: {detail}")
            return None
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Could not reach the VM backend: {exc}")
        return None

health = backend_health()
st.markdown("<section class='hero'><div class='kicker'>AVIATOR M6 / REMOTE INFERENCE</div><h1>Calibrated multiplier analytics</h1><p>Streamlit Cloud is the presentation layer. The private M6 model and Groq integration remain on the VM.</p></section>", unsafe_allow_html=True)
status = "ONLINE" if health.get("status") == "online" else "OFFLINE"
st.markdown(f"<div class='metric'>Backend status<strong>{status}</strong><span class='muted'>{health.get('dataset_rows', '—')} dataset rows</span></div>", unsafe_allow_html=True)
left, right = st.columns([1.1, .9], gap="large")
with left:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Analyze recent rounds")
    mode = st.radio("Input mode", ["Two rounds", "One round"], horizontal=True)
    text = st.text_input("Chronological multipliers", value="1.12, 1.25" if mode == "Two rounds" else "1.25", help="Use one or two values, for example 1.12, 1.25")
    analyze = st.button("Analyze next round", type="primary", use_container_width=True)
    if analyze:
        try:
            rounds = parse_rounds_text(text)
            with st.spinner("Running M6 inference on the VM..."):
                result = call_prediction(rounds)
            if result:
                st.session_state["latest_result"] = result
                st.session_state.setdefault("history", []).insert(0, {"time":datetime.now().strftime("%H:%M:%S"), "rounds":rounds, "range":result["prediction"]["estimated_range"]})
                st.session_state["history"] = st.session_state["history"][:10]
        except ValueError as exc:
            st.error(str(exc))
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    result = st.session_state.get("latest_result")
    if result:
        prediction = result["prediction"]
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Latest model result")
        m1, m2 = st.columns(2); m1.metric("Model", prediction["model_type"].replace("_", " ").title()); m2.metric("Confidence", prediction["confidence_level"])
        st.markdown(f"**Estimated range:** `{prediction['estimated_range']}`")
        st.bar_chart(result["probabilities"], height=230)
        st.info(result.get("ai_explanation") or "No explanation returned.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='panel'><h3>Awaiting analysis</h3><p class='muted'>Submit one or two recent rounds to request a model result from the VM.</p></div>", unsafe_allow_html=True)
st.subheader("Session history")
for item in st.session_state.get("history", []):
    st.write(f"{item['time']} | {item['rounds']} | {item['range']}")
st.markdown("<div class='disclaimer'>Predictions are experimental statistical estimates and are not guaranteed. This dashboard is for analytics/research purposes only.</div>", unsafe_allow_html=True)
