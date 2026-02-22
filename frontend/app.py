# app.py
import requests
import streamlit as st

API_BASE = "http://localhost:8000"  # FastAPI URL

st.set_page_config(page_title="Ripplect Dev Panel", layout="wide")
st.title("Ripplect Dev Panel (Backend Smoke Test)")

@st.cache_data
def fetch_crises():
    r = requests.get(f"{API_BASE}/crises/")
    r.raise_for_status()
    return r.json()

crises = fetch_crises()
if not crises:
    st.warning("No crises loaded from backend.")
    st.stop()

name_to_id = {c["name"]: c["id"] for c in crises}

col_sidebar, col_main = st.columns([1, 2])

with col_sidebar:
    st.subheader("Test Scenario Input")
    crisis_name = st.selectbox("Crisis", list(name_to_id.keys()))
    crisis_id = name_to_id[crisis_name]

    health_delta = st.slider("Health funding Δ (USD)", -5_000_000, 5_000_000, 0, 250_000)
    wash_delta = st.slider("WASH funding Δ (USD)", -5_000_000, 5_000_000, 0, 250_000)

    inflation_pct = st.slider("Inflation shock (%)", 0, 100, 0)
    drought = st.checkbox("Drought shock")
    conflict_intensity = st.slider("Conflict intensity", 0.0, 1.0, 0.0, 0.1)

    what_if_text = st.text_area("What-if text (for memo testing)", "")

    if st.button("Run /simulate"):
        payload = {
            "crisis_id": crisis_id,
            "funding_changes": [
                {"sector": "Health", "delta_usd": health_delta},
                {"sector": "WASH", "delta_usd": wash_delta},
            ],
            "shock": {
                "inflation_pct": inflation_pct,
                "drought": drought,
                "conflict_intensity": conflict_intensity,
            },
            "what_if_text": what_if_text,
        }
        sim = requests.post(f"{API_BASE}/simulate/", json=payload)
        if sim.ok:
            st.session_state["sim"] = sim.json()
        else:
            st.error(f"Sim error: {sim.status_code} {sim.text}")

with col_main:
    st.subheader("Simulation Output")
    sim = st.session_state.get("sim")
    if sim:
        st.json(sim)
    else:
        st.info("Run a scenario to see /simulate output.")

st.divider()
st.subheader("Quick /crises check")
st.table(crises[:5])
