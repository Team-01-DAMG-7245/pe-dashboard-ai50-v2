import streamlit as st
import requests
import os

# FastAPI base URL
API_BASE = os.getenv("FASTAPI_URL", "http://localhost:8000")

st.set_page_config(page_title="PE Dashboard (AI 50)", layout="wide")
st.title("Project ORBIT – PE Dashboard for Forbes AI 50")

# Fetch companies
try:
    companies = requests.get(f"{API_BASE}/companies", timeout=5).json()
except Exception as e:
    st.error(f"Could not connect to API: {e}")
    companies = []

if not companies:
    st.warning("No companies available. Please run the Airflow DAG first.")
    st.stop()

# Company selector
names = [c["company_name"] for c in companies]
choice = st.selectbox("Select company", names)

# Get company_id for selected company
selected = next((c for c in companies if c["company_name"] == choice), None)
company_id = selected.get("company_id", choice.lower().replace(' ', '_')) if selected else choice.lower().replace(' ', '_')

# Display company info
if selected:
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Location", f"{selected.get('hq_city', 'N/A')}, {selected.get('hq_country', 'N/A')}")
    with col2:
        st.metric("Category", selected.get('category', 'N/A'))
    with col3:
        if selected.get('website'):
            st.markdown(f"[Website]({selected['website']})")

st.markdown("---")

# Two-column layout for pipelines
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Structured Pipeline")
    st.caption("Uses Pydantic-extracted data")
    
    if st.button("Generate (Structured)", key="structured", use_container_width=True):
        with st.spinner("Generating dashboard..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/dashboard/structured",
                    params={"company_id": company_id},
                    timeout=30
                )
                if resp.status_code == 200:
                    st.markdown(resp.json()["markdown"])
                else:
                    st.error(f"Error {resp.status_code}: {resp.text}")
            except Exception as e:
                st.error(f"Failed: {e}")

with col2:
    st.subheader("🔍 RAG Pipeline")
    st.caption("Uses vector database retrieval")
    
    if st.button("Generate (RAG)", key="rag", use_container_width=True):
        with st.spinner("Generating dashboard..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/dashboard/rag",
                    params={"company_name": choice},
                    timeout=30
                )
                if resp.status_code == 200:
                    result = resp.json()
                    st.markdown(result["markdown"])
                    with st.expander("📄 Retrieved context"):
                        st.json(result.get("retrieved", []))
                else:
                    st.error(f"Error {resp.status_code}: {resp.text}")
            except Exception as e:
                st.error(f"Failed: {e}")