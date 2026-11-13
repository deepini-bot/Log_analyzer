import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

API = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="LogMind", page_icon="🧠", layout="wide")
st.title("🧠 LogMind")
st.caption("AI-powered log anomaly detection and incident investigation")

with st.sidebar:
    st.header("Ingest logs")
    upload = st.file_uploader("Upload .log or .txt", type=["log", "txt"])
    if upload and st.button("Analyze logs", type="primary"):
        try:
            r = requests.post(API + "/ingest", files={"file": (upload.name, upload.getvalue())}, timeout=90)
            r.raise_for_status()
            st.session_state["result"] = r.json()
            st.success(f"Processed {r.json()['event_count']} events")
        except Exception as e:
            st.error(f"API error: {e}")
    if st.button("Refresh"):
        st.rerun()

try:
    incidents = requests.get(API + "/incidents", timeout=15).json()
except Exception:
    incidents = []
    st.error("API unavailable. Start it with: uvicorn app.main:app --reload")

if "result" in st.session_state:
    result = st.session_state["result"]
    a, b, c = st.columns(3)
    a.metric("Events processed", result["event_count"])
    b.metric("Anomalies detected", result["anomaly_count"])
    c.metric("Incidents created", len(result["incidents"]))
    if result.get("temporal_spikes"):
        st.subheader("Temporal spikes")
        st.dataframe(pd.DataFrame(result["temporal_spikes"]), use_container_width=True)

st.subheader("Incident overview")
if incidents:
    frame = pd.DataFrame([{"ID": x["incident_id"], "Title": x["title"], "Severity": x["severity"],
                           "Events": x["event_count"], "Start": x["start_time"]} for x in incidents])
    col1, col2 = st.columns([1, 2])
    with col1:
        st.plotly_chart(px.pie(frame, names="Severity", title="Incidents by severity"), use_container_width=True)
    with col2:
        st.dataframe(frame, use_container_width=True, hide_index=True)
    chosen = st.selectbox("Investigate incident", [x["incident_id"] for x in incidents])
    incident = next(x for x in incidents if x["incident_id"] == chosen)
    st.markdown("### " + incident["title"])
    st.write(incident["summary"])
    st.caption(f'{incident["severity"].upper()} · {incident["event_count"]} events')
    st.dataframe(pd.DataFrame(incident["events"]), use_container_width=True, hide_index=True)
    if st.button("Run AI investigation", type="primary"):
        try:
            response = requests.post(API + f"/investigate/{chosen}", timeout=90)
            response.raise_for_status()
            st.session_state["investigation"] = response.json()
        except Exception as e:
            st.error(f"Investigation failed: {e}")
    if st.session_state.get("investigation"):
        inv = st.session_state["investigation"]
        st.subheader("Investigation result")
        st.info(inv.get("warning", "Validate findings before acting."))
        st.write(inv.get("analysis"))
        with st.expander("Evidence and retrieved context"):
            st.write(inv.get("evidence"))
            st.write(inv.get("retrieved_context"))
else:
    st.info("Upload a log file to begin.")
