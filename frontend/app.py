# app.py – AidSight Dev Panel (wired to /crises, /simulate, /twins, /memos)
import requests

import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="AidSight Dev Panel", layout="wide")
st.title("AidSight Dev Panel")


@st.cache_data(ttl=60)
def fetch_crises():
    r = requests.get(f"{API_BASE}/crises/", timeout=10)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=60)
def fetch_projects():
    r = requests.get(f"{API_BASE}/projects/", timeout=10)
    r.raise_for_status()
    return r.json()


def run_smoke_test():
    """Run internal smoke test and display results."""
    try:
        r = requests.get(f"{API_BASE}/debug/data-status", timeout=10)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


# --- Crises ---
try:
    crises = fetch_crises()
except Exception as e:
    st.error(f"Cannot reach /crises: {e}")
    st.stop()

if not crises:
    st.warning("No crises loaded from backend.")
    st.stop()

name_to_id = {c["name"]: c["id"] for c in crises}

# --- Projects (for twins) ---
try:
    projects = fetch_projects()
except Exception:
    projects = []

project_options = {f"{p.get('name', p.get('id', p['id']))} ({p['id']})": p["id"] for p in projects} if projects else {}

# --- Layout ---
col_sidebar, col_main = st.columns([1, 2])

with col_sidebar:
    st.subheader("Scenario Input")
    crisis_name = st.selectbox("Crisis", list(name_to_id.keys()))
    crisis_id = name_to_id[crisis_name]

    health_delta = st.slider("Health funding Δ (USD)", -5_000_000, 5_000_000, 0, 250_000)
    wash_delta = st.slider("WASH funding Δ (USD)", -5_000_000, 5_000_000, 0, 250_000)
    inflation_pct = st.slider("Inflation shock (%)", 0, 100, 0)
    drought = st.checkbox("Drought shock")
    conflict_intensity = st.slider("Conflict intensity", 0.0, 1.0, 0.0, 0.1)
    what_if_text = st.text_area("What-if text (for memo)", "")

    scenario_payload = {
        "crisis_id": crisis_id,
        "funding_changes": [
            {"sector": "Health", "delta_usd": health_delta},
            {"sector": "WASH", "delta_usd": wash_delta},
        ],
        "shock": {
            "inflation_pct": float(inflation_pct),
            "drought": drought,
            "conflict_intensity": conflict_intensity,
        },
        "what_if_text": what_if_text or None,
    }

    if st.button("Run /simulate"):
        try:
            sim = requests.post(f"{API_BASE}/simulate/", json=scenario_payload, timeout=15)
            if sim.ok:
                st.session_state["sim"] = sim.json()
            else:
                err = sim.json().get("detail", sim.text) if sim.headers.get("content-type", "").startswith("application/json") else sim.text
                st.error(f"Sim error: {sim.status_code} – {err}")
        except Exception as e:
            st.error(f"Request failed: {e}")

with col_main:
    st.subheader("Simulation Output (/simulate)")
    sim = st.session_state.get("sim")
    if sim:
        st.json(sim)
    else:
        st.info("Run a scenario to see /simulate output.")

st.divider()

# --- Memos ---
st.subheader("Contrarian Memo (/memos)")
if sim:
    project_for_twin = None
    if project_options:
        project_label = st.selectbox("Project for Success Twin (optional)", ["None"] + list(project_options.keys()))
        if project_label and project_label != "None":
            project_for_twin = project_options[project_label]

    if st.button("Generate memo"):
        payload = {"crisis_id": crisis_id, "simulation": sim}
        if project_for_twin:
            try:
                twin_r = requests.get(f"{API_BASE}/twins/{project_for_twin}", timeout=15)
                if twin_r.ok:
                    payload["twin"] = twin_r.json()
            except Exception:
                pass
        try:
            memo_r = requests.post(f"{API_BASE}/memos/", json=payload, timeout=15)
            if memo_r.ok:
                memo = memo_r.json()
                st.session_state["memo"] = memo
            else:
                err = memo_r.json().get("detail", memo_r.text) if memo_r.headers.get("content-type", "").startswith("application/json") else memo_r.text
                st.error(f"Memo error: {memo_r.status_code} – {err}")
        except Exception as e:
            st.error(f"Request failed: {e}")

    memo = st.session_state.get("memo")
    if memo:
        st.markdown(f"**{memo.get('title', 'Memo')}**")
        st.write(memo.get("body", ""))
        if memo.get("key_risks"):
            st.write("Key risks:", ", ".join(memo["key_risks"]))
else:
    st.info("Run a simulation first, then generate memo.")

st.divider()

# --- Success Twins ---
st.subheader("Success Twin (/twins)")
if project_options:
    twin_project_label = st.selectbox("Project to find twin for", list(project_options.keys()), key="twin_select")
    twin_project_id = project_options[twin_project_label]
    if st.button("Get Success Twin"):
        try:
            twin_r = requests.get(f"{API_BASE}/twins/{twin_project_id}", timeout=30)
            if twin_r.ok:
                twin = twin_r.json()
                st.session_state["twin"] = twin
            else:
                err = twin_r.json().get("detail", twin_r.text) if twin_r.headers.get("content-type", "").startswith("application/json") else twin_r.text
                st.error(f"Twins error: {twin_r.status_code} – {err}")
        except Exception as e:
            st.error(f"Request failed: {e}")

    twin = st.session_state.get("twin")
    if twin:
        st.write(f"**Target:** {twin.get('target_project_id', '')}")
        st.write(f"**Twin:** {twin.get('twin_project_id', '')} (similarity: {twin.get('similarity_score', 0):.3f})")
        for b in twin.get("bullets", []):
            st.write(f"- {b}")
else:
    st.warning("No projects available for Success Twin.")

st.divider()

# --- Data status / smoke test ---
st.subheader("Data Status")
if st.button("Refresh data status"):
    status = run_smoke_test()
    if status:
        st.json(status)
    else:
        st.warning("Could not fetch /debug/data-status (backend may not be running).")

st.subheader("Crises (first 5)")
st.table(crises[:5])



