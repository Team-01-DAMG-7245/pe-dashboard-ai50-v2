import streamlit as st
import requests
import os

# Use environment variable if available (for Docker), otherwise fallback to localhost
API_BASE = os.getenv("FASTAPI_URL", "http://localhost:8002")

st.set_page_config(page_title="PE Dashboard (AI 50)", layout="wide")
st.title("Project ORBIT – PE Dashboard for Forbes AI 50")

# Get list of companies from API
try:
    response = requests.get(f"{API_BASE}/companies", timeout=30)
    if response.status_code == 200:
        companies_data = response.json()
        # Handle both list and dict responses
        if isinstance(companies_data, list):
            # API returns list of company objects directly
            company_list = [company.get("company_name", "") for company in companies_data if company.get("company_name")]
        elif isinstance(companies_data, dict):
            # API returns dict with "companies" key
            company_list = companies_data.get("companies", [])
        else:
            company_list = []
    else:
        company_list = []
        st.warning("Could not fetch companies from API. Please ensure the API server is running.")
except Exception as e:
    company_list = []
    st.error(f"Error connecting to API: {e}. Please ensure the API server is running at {API_BASE}")

# Generate company IDs (lowercase, normalized) for API calls
def generate_company_id(company_name):
    """Generate company_id from company name"""
    if not company_name:
        return ""
    return company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')

# Company selection dropdown
if company_list:
    selected_company_name = st.selectbox("Select Company", company_list, key="company_selector")
    selected_company = generate_company_id(selected_company_name)
else:
    default_companies = ["anthropic", "abridge", "baseten", "clay", "anysphere"]
    selected_company = st.selectbox("Select Company", default_companies, key="company_selector")
    selected_company_name = selected_company
    st.info("Using default company list. API may not be available.")

st.divider()

# Two columns for RAG and Structured pipelines
col1, col2 = st.columns(2)

# Column 1: Structured Pipeline
with col1:
    st.subheader("📊 Structured Pipeline Dashboard")
    st.caption("Uses normalized structured payload (JSON) → LLM → Dashboard")
    
    if st.button("Generate Structured Dashboard", key="structured_btn", type="primary"):
        with st.spinner(f"Generating structured dashboard for {selected_company}..."):
            try:
                response = requests.post(
                    f"{API_BASE}/dashboard/structured",
                    json={"company_id": selected_company},
                    timeout=300,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # API returns "markdown" key, not "dashboard"
                    dashboard = data.get("markdown", data.get("dashboard", ""))
                    st.success("✅ Dashboard generated successfully!")
                    if dashboard:
                        st.markdown(dashboard)
                    else:
                        st.warning("Dashboard content is empty")
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to API: {e}")
            except Exception as e:
                st.error(f"Error generating dashboard: {e}")

# Column 2: RAG Pipeline
with col2:
    st.subheader("🔍 RAG Pipeline Dashboard")
    st.caption("Uses vector DB retrieval → LLM → Dashboard")
    
    top_k = st.slider("Top K chunks to retrieve", min_value=5, max_value=20, value=10, key="top_k_slider")
    
    if st.button("Generate RAG Dashboard", key="rag_btn", type="primary"):
        with st.spinner(f"Generating RAG dashboard for {selected_company}..."):
            try:
                response = requests.post(
                    f"{API_BASE}/dashboard/rag",
                    json={"company_id": selected_company},
                    timeout=300,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # API returns "markdown" key, not "dashboard"
                    dashboard = data.get("markdown", data.get("dashboard", ""))
                    chunks_used = data.get("chunks_used", 0)
                    st.success(f"✅ Dashboard generated successfully! (Used {chunks_used} chunks)")
                    if dashboard:
                        st.markdown(dashboard)
                    else:
                        st.warning("Dashboard content is empty")
                    
                    with st.expander("📋 Retrieval Details"):
                        st.info(f"Retrieved {chunks_used} chunks from vector database for context.")
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to API: {e}")
            except Exception as e:
                st.error(f"Error generating dashboard: {e}")

# Footer
st.divider()
st.caption(f"API Server: {API_BASE} | Health Check: {API_BASE}/health")
