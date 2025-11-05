# Forbes AI 50 - PE Dashboard (Project ORBIT)

Automated data pipeline for scraping and analyzing Forbes AI 50 companies for private equity intelligence.

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
OPENAI_API_KEY=your-api-key-here
```

---

## Running Labs 4-9

### Prerequisites

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Set environment variables
$env:PYTHONPATH = ".;src"
$env:OPENAI_API_KEY = (Get-Content .env | Select-String "OPENAI_API_KEY" | ForEach-Object { $_.Line -replace '.*=', '' }).Trim()
```

### Step 1: Lab 4 - Vector DB & RAG Index

**Build Vector DB Index:**
```powershell
python src\lab4\index_for_rag_all.py
```

**Expected Output:** Vector DB should have 294+ chunks indexed.

**Verify:**
```powershell
Get-ChildItem data\vector_db -Recurse | Measure-Object
```

### Step 2: Lab 5 - Structured Extraction

**Extract Structured Data:**
```powershell
python src\lab5\structured_extraction.py
```

**Expected Output:** At least 5 companies with structured data in `data/structured/`.

**Verify:**
```powershell
Get-ChildItem data\structured -Filter *.json | Measure-Object
```

### Step 3: Lab 6 - Payload Validation

**Validate Payloads:**
```powershell
python src\lab6\test_validation.py
```

**Expected Output:** 5/5 payloads validate successfully.

### Step 4: Lab 7 & 8 - Dashboard API

**Start API Server:**
```powershell
python src\lab7\rag_dashboard.py
```

**Access API:**
- Health: http://localhost:8002/health
- Swagger UI: http://localhost:8002/docs
- RAG Dashboard: `POST http://localhost:8002/dashboard/rag`
- Structured Dashboard: `POST http://localhost:8002/dashboard/structured`

**Test Lab 7 (RAG Dashboard):**
```powershell
$body = @{company_id="anthropic"; top_k=10} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8002/dashboard/rag" -Method Post -Body $body -ContentType "application/json"
```

**Test Lab 8 (Structured Dashboard):**
```powershell
$body = @{company_id="anthropic"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8002/dashboard/structured" -Method Post -Body $body -ContentType "application/json"
```

**Expected Output:**
- Lab 7: Generates 8-section dashboard using RAG pipeline with "Not disclosed." for missing data
- Lab 8: Generates 8-section dashboard using structured payload (more precise)

### Step 5: Lab 9 - Evaluation & Comparison

**Generate Evaluation Dashboards:**
```powershell
# Ensure Lab 7/8 API is running first
python src\lab9\evaluate_comparison.py
```

**Output:** Dashboards saved in `evaluation_output/` directory.

**Fill Evaluation:**
- Review dashboards in `evaluation_output/`
- Fill out `EVAL.md` with rubric scores (0-10 points per company)
- Complete comparison of RAG vs Structured methods

**Expected Output:** `EVAL.md` with rubric and scores for 5+ companies.

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

### ✅ Lab 4: Vector DB & RAG Index
- Chunk text into 500-1000 tokens
- Embed and store in vector DB (ChromaDB)
- FastAPI endpoint: `/rag/search` (Lab 4 API on port 8001)

### ✅ Lab 5: Structured Extraction (Pydantic)
- Use `instructor` library with LLM
- Extract: Company, Event, Snapshot, Product, Leadership, Visibility
- Output: `data/structured/<company_id>.json`

### ✅ Lab 6: Payload Assembly
- Combine all structured data into dashboard payload
- Output: `data/payloads/<company_id>.json`
- Validation: All payloads can be loaded by `src/structured_pipeline.py`

### ✅ Lab 7: RAG Pipeline Dashboard
- Endpoint: `POST /dashboard/rag`
- Vector DB → LLM → 8-section Markdown dashboard
- Uses "Not disclosed." for missing data

### ✅ Lab 8: Structured Pipeline Dashboard
- Endpoint: `POST /dashboard/structured`
- Pydantic payload → LLM → Markdown dashboard
- More precise and less hallucinatory than RAG

### ✅ Lab 9: Evaluation & Comparison
- Compare RAG vs Structured for 5+ companies
- Rubric: factual correctness, schema adherence, hallucination control
- Output: `EVAL.md` with scores and findings

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

# Labs 4-9 - Complete Sequence
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = ".;src"
$env:OPENAI_API_KEY = (Get-Content .env | Select-String "OPENAI_API_KEY" | ForEach-Object { $_.Line -replace '.*=', '' }).Trim()
# Step 1: Lab 4
python src\lab4\index_for_rag_all.py
# Step 2: Lab 5
python src\lab5\structured_extraction.py
# Step 3: Lab 6
python src\lab6\test_validation.py
# Step 4: Lab 7/8 (run in separate terminal)
python src\lab7\rag_dashboard.py
# Step 5: Lab 9 (after API is running)
python src\lab9\evaluate_comparison.py
```

---

## Troubleshooting

**DLL Errors (Windows):**
- Install Visual C++ Redistributables: https://aka.ms/vs/17/release/vc_redist.x64.exe
- Restart terminal after installation

**API Not Starting:**
- Check if port 8002 is available
- Verify `.env` file has `OPENAI_API_KEY` set
- Ensure virtual environment is activated

**Vector DB Empty:**
- Run `python src\index_for_rag_all.py` to populate vector DB
- Check that `data/raw/` contains company directories

**Docker Issues:**
- Ensure Docker Desktop is running
- Check `docker-compose.yml` configuration
- View logs: `docker compose logs -f`

---

## Deliverables

- [x] GitHub repo: `pe-dashboard-ai50`
- [x] Working Airflow DAGs (Lab 2-3)
- [x] FastAPI with `/dashboard/rag`, `/dashboard/structured`
- [x] Vector DB with ChromaDB (Lab 4)
- [x] Structured extraction with Pydantic (Lab 5)
- [x] Payload assembly and validation (Lab 6)
- [x] RAG pipeline dashboard (Lab 7)
- [x] Structured pipeline dashboard (Lab 8)
- [x] `EVAL.md` comparing RAG vs Structured (5+ companies) (Lab 9)
- [ ] Streamlit UI with company dropdown → dashboard
- [ ] Docker for FastAPI + Streamlit
- [ ] Demo video ≤10 mins
- [ ] Contribution attestation
