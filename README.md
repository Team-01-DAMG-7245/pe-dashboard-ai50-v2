# Forbes AI 50 - PE Dashboard (Project ORBIT)

Automated data pipeline for scraping and analyzing Forbes AI 50 companies for private equity intelligence.

**Assignment 2 — DAMG7245**

---

## Quick Start

### Run Airflow (Docker)
```bash
docker compose up
# Access UI: http://localhost:8080 (admin/admin)
```

### Run App Locally (Dev)
```bash
python -m venv airflow_env
source airflow_env/bin/activate
pip install -r requirements.txt
uvicorn src.api:app --reload        # http://localhost:8000
streamlit run src/streamlit_app.py  # http://localhost:8501
```

---

## Project Structure

```
├── dags/                  # Airflow DAGs (Labs 2-3)
├── data/
│   ├── forbes_ai50_seed.json   # Company list (Lab 0)
│   ├── raw/                     # Scraped HTML/text (Lab 1)
│   ├── structured/              # Pydantic models (Lab 5)
│   └── payloads/                # Dashboard payloads (Lab 6)
├── src/
│   ├── api.py                   # FastAPI endpoints (Lab 7-8)
│   ├── models.py                # Pydantic schemas (Lab 5)
│   ├── s3_utils.py              # Cloud storage (Lab 1)
│   └── streamlit_app.py         # Dashboard UI (Lab 10)
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## Setup

### 1. AWS S3 Configuration
```bash
aws configure  # Enter your credentials
export AWS_BUCKET_NAME=quanta-ai50-data
```

### 2. Seed File
Populate `data/forbes_ai50_seed.json` with Forbes AI 50 companies from https://www.forbes.com/lists/ai50/

### 3. Environment Variables
Create `.env`:
```bash
AWS_BUCKET_NAME=quanta-ai50-data
```

---

## Labs Progress

### ✅ Lab 0: Project Bootstrap
- Repository structure with `dags/`, `data/`, `src/`
- `forbes_ai50_seed.json` with all 50 companies

### ✅ Lab 1: Scrape & Store
- Python scraper for homepage, about, product, careers, blog
- Stores raw HTML + clean text locally
- Uploads to S3: `s3://quanta-ai50-data/ai50/raw/`

### ✅ Lab 2: Full Load Airflow DAG
- `ai50_full_ingest_dag.py` - scrapes all 50 companies
- Schedule: `@once` (manual trigger)
- Output: `data/raw/<company_id>/initial/` + S3

### ✅ Lab 3: Daily Refresh Airflow DAG
- `ai50_daily_refresh_dag.py` - daily updates
- Schedule: `0 3 * * *` (3 AM UTC)
- Tracks changes with content hashing
- Creates dated subfolders per run

### 🔄 Lab 4: Vector DB & RAG Index
- Chunk text into 500-1000 tokens
- Embed and store in vector DB (FAISS/Chroma)
- FastAPI endpoint: `/rag/search`

### 🔄 Lab 5: Structured Extraction (Pydantic)
- Use `instructor` library with LLM
- Extract: Company, Event, Snapshot, Product, Leadership, Visibility
- Output: `data/structured/<company_id>.json`

### 🔄 Lab 6: Payload Assembly
- Combine all structured data into dashboard payload
- Output: `data/payloads/<company_id>.json`

### 🔄 Lab 7: RAG Pipeline Dashboard
- Endpoint: `POST /dashboard/rag`
- Vector DB → LLM → 8-section Markdown dashboard

### 🔄 Lab 8: Structured Pipeline Dashboard
- Endpoint: `POST /dashboard/structured`
- Pydantic payload → LLM → Markdown dashboard

### 🔄 Lab 9: Evaluation & Comparison
- Compare RAG vs Structured for 5+ companies
- Rubric: factual correctness, schema adherence, hallucination control
- Output: `EVAL.md`

### 🔄 Lab 10: Dockerize FastAPI + Streamlit
- `docker-compose.yml` for app layer
- FastAPI: http://localhost:8000
- Streamlit: http://localhost:8501

### 🔄 Lab 11: DAG ↔ App Integration
- Daily DAG writes to `data/payloads/`
- App reads from payloads for dashboard generation

---

## Key Commands

```bash
# Airflow
docker compose up               # Start Airflow
docker compose down             # Stop Airflow
docker compose logs -f          # View logs

# Check S3
aws s3 ls s3://quanta-ai50-data/ai50/raw/

# Check scraped data
ls data/raw/ | wc -l           # Count companies scraped
```

---

## Deliverables

- [x] GitHub repo: `pe-dashboard-ai50`
- [x] Working Airflow DAGs (Lab 2-3)
- [ ] FastAPI with `/companies`, `/dashboard/rag`, `/dashboard/structured`
- [ ] Streamlit UI with company dropdown → dashboard
- [ ] Docker for FastAPI + Streamlit
- [ ] `EVAL.md` comparing RAG vs Structured (5+ companies)
- [ ] Demo video ≤10 mins
- [ ] Contribution attestation