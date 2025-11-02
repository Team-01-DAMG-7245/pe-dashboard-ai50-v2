# Project ORBIT — PE Dashboard for Forbes AI 50

This is the starter package for **Assignment 2 — DAMG7245**.

## Run locally (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api:app --reload
# in another terminal
streamlit run src/streamlit_app.py
```

## Docker (app layer only)

```bash
cd docker
docker compose up --build
```

This starts:
- FastAPI: http://localhost:8000
- Streamlit: http://localhost:8501

# Add instructions on running on the cloud based on your setup and links to Codelabs, architecture diagrams etc.

---

# Lab 0 — Project Bootstrap & AI 50 Seed

## How to Implement

### 1. Install Dependencies

Navigate to the Lab0 directory and install the required packages:

```bash
cd src/Lab0
pip install -r requirements.txt
```

**Note:** If using Selenium, ensure ChromeDriver is installed:
- Download ChromeDriver from https://chromedriver.chromium.org/
- Add it to your system PATH, or
- Use `webdriver-manager` package (optional) for automatic driver management

### 2. Run the Scraper

Execute the scraper script to fetch and populate the Forbes AI 50 data:

```bash
python scrape_forbes_ai50.py
```

This will:
- Fetch data from https://www.forbes.com/lists/ai50/
- Parse company information
- Save results to `../../data/forbes_ai50_seed.json`

### 3. Verify Output

Check that the seed file was created:

```bash
ls ../../data/forbes_ai50_seed.json
```

The JSON file should contain 50 company entries with the following schema:

```json
[
  {
    "rank": 1,
    "company_name": "Company Name",
    "description": "Brief description",
    "industry": "Industry sector",
    "location": "Headquarters location",
    "year_founded": 2020,
    "funding": "$100M",
    "valuation": "$1B"
  }
]
```

### 4. Troubleshooting

**If the scraper creates template data instead of real data:**

1. Forbes website may use JavaScript rendering that requires Selenium
2. Website structure may have changed
3. Check if ChromeDriver is properly installed and accessible

**Manual Fallback:**
If automated scraping fails, manually populate `data/forbes_ai50_seed.json` with data from https://www.forbes.com/lists/ai50/

### Checkpoint

After successful implementation:
- ✅ `data/forbes_ai50_seed.json` exists
- ✅ File contains 50 company entries
- ✅ All required fields are populated (rank, company_name at minimum)

---

# Lab 1 — Scrape & Store

## Goal

Pull source pages from company websites and store them locally (or to cloud storage). Each company gets a folder with subfolders for initial pull and subsequent daily runs.

## How to Implement

### 1. Install Dependencies

Navigate to the Lab1 directory and install the required packages:

```bash
cd src/Lab1
pip install -r requirements.txt
```

### 2. Run the Scraper

Execute the scraper script to fetch company website pages:

```bash
# Scrape all companies (initial run)
python scrape_company_pages.py

# Or limit to first N companies for testing
python scrape_company_pages.py --limit 5

# For daily runs (stores in daily/ subfolder)
python scrape_company_pages.py --run-type daily
```

This will:
- Read companies from `../../data/forbes_ai50_seed.json`
- For each company, scrape 5 page types:
  - **homepage** (root `/`)
  - **about** (`/about`, `/about-us`, etc.)
  - **product/platform** (`/product`, `/platform`, `/solutions`, etc.)
  - **careers** (`/careers`, `/jobs`, etc.)
  - **blog/news** (`/blog`, `/news`, `/press`, etc.)
- Save raw HTML (`.html`) and clean text (`.txt`) for each page
- Generate metadata JSON for each page
- Organize files in `data/raw/<company_id>/initial/` structure

### 3. Output Structure

Each company's data is organized as:

```
data/raw/
├── <company_id>/
│   └── initial/              # or daily/ for daily runs
│       ├── homepage.html     # Raw HTML
│       ├── homepage.txt      # Clean text
│       ├── homepage_metadata.json
│       ├── about.html
│       ├── about.txt
│       ├── about_metadata.json
│       ├── product.html
│       ├── product.txt
│       ├── product_metadata.json
│       ├── careers.html
│       ├── careers.txt
│       ├── careers_metadata.json
│       ├── blog.html
│       ├── blog.txt
│       └── blog_metadata.json
└── scrape_summary_initial_<timestamp>.json
```

### 4. Metadata Format

Each page's metadata JSON contains:

```json
{
  "company_name": "Abridge",
  "company_id": "abridge",
  "page_type": "homepage",
  "source_url": "https://www.abridge.com/",
  "crawled_at": "2025-11-01T16:18:35.511992Z",
  "content_length": 193487,
  "text_length": 4851
}
```

**Required fields** (per spec):
- ✅ `company_name`: Company name
- ✅ `source_url`: URL of the scraped page
- ✅ `crawled_at`: ISO 8601 timestamp in UTC

**Additional fields** (useful for processing):
- `company_id`: Safe identifier for folder naming
- `page_type`: Type of page (homepage, about, product, etc.)
- `content_length`: Size of HTML in bytes
- `text_length`: Size of clean text in characters

### 5. Command-Line Options

```bash
python scrape_company_pages.py --help

Options:
  --seed-file PATH     Path to seed JSON file (default: ../../data/forbes_ai50_seed.json)
  --data-dir PATH      Base directory for storing data (default: ../../data/raw)
  --run-type TYPE      Type of run: initial or daily (default: initial)
  --limit N            Limit number of companies to scrape (for testing)
```

### Checkpoint



# Forbes AI50 PE Dashboard - Labs 4-7 Documentation

## Overview
This document covers the implementation of Labs 4-7 for the Forbes AI50 Private Equity Dashboard project. These labs focus on knowledge representation and dashboard generation.

---

## Lab 4: Vector DB & RAG Index
**Status:** ✅ Complete  
**Files:** `src/api_rag.py`, `src/vector_db.py`, `src/chunker.py`  
**Port:** 8001

### Description
Implements a Retrieval-Augmented Generation (RAG) system using ChromaDB for vector storage and semantic search.

### Key Components
- **Text Chunker**: Splits company data into 500-1000 token chunks with overlap
- **Vector Database**: ChromaDB persistent storage with embeddings
- **Search API**: FastAPI endpoint for semantic search

### Setup & Usage
```bash
# Install dependencies
pip install chromadb sentence-transformers fastapi uvicorn tiktoken

# Run the API
python src/api_rag.py

# Test search endpoint
curl -X POST "http://localhost:8001/rag/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI products", "company_id": "anthropic", "n_results": 5}'
```

### Implementation Details
- Embedding Model: `all-MiniLM-L6-v2`
- Chunk Size: 750 tokens (target), 1000 tokens (max)
- Overlap: 100 tokens
- Vector DB Path: `data/vector_db/`

---

## Lab 5: Structured Extraction with Pydantic
**Status:** ✅ Complete  
**Files:** `src/extract_structured.py`  
**Output:** `data/structured/company_name.json`

### Description
Extracts structured information from raw company data using OpenAI GPT-4 and Pydantic models.

### Key Components
- **Pydantic Models**: Structured schemas for company information
- **OpenAI Integration**: GPT-4 for intelligent extraction
- **Instructor Library**: Ensures structured output compliance

### Setup & Usage
```bash
# Install dependencies
pip install openai instructor pydantic

# Set OpenAI API key
export OPENAI_API_KEY="your-key-here"

# Run extraction for 5 test companies
python src/extract_structured.py

# Check output
ls data/structured/
```

### Extracted Fields
- Company overview (name, description, industry, location)
- Leadership team (executives with roles and backgrounds)
- Funding information (total raised, last round, valuation)
- Products and services
- Target customers
- Recent news

### Test Companies
- anthropic
- databricks
- openevidence
- cohere
- glean

---

## Lab 6: Payload Assembly
**Status:** ✅ Complete  
**Files:** `src/assemble_payloads.py`  
**Output:** `data/payloads/company_name.json`

### Description
Assembles complete structured payloads from extracted data components, validated against the pipeline schema.

### Key Components
- **Payload Assembly**: Combines all JSON components
- **Validation**: Ensures schema compliance
- **Test Suite**: Validates with `structured_pipeline.py`

### Setup & Usage
```bash
# Run payload assembly
python src/assemble_payloads.py

# Validate payloads
python src/structured_pipeline.py

# Check assembled payloads
ls data/payloads/
```

### Payload Structure
```json
{
  "company_id": "string",
  "overview": {...},
  "leadership": [...],
  "funding": {...},
  "products": [...],
  "customers": [...],
  "news": [...]
}
```

---

## Lab 7: RAG Pipeline Dashboard
**Status:** ✅ Complete  
**Files:** `src/rag_dashboard.py`, `src/index_for_rag.py`  
**Port:** 8002

### Description
Generates 8-section investor dashboards using vector DB retrieval and LLM synthesis.

### Key Components
- **Vector Retrieval**: Searches relevant chunks from ChromaDB
- **Dashboard Generation**: Creates structured investor reports
- **Prompt Engineering**: Follows strict 8-section format

### Dashboard Sections
1. Company Overview
2. Business Model and GTM
3. Funding & Investor Profile
4. Growth Momentum
5. Visibility & Market Sentiment
6. Risks and Challenges
7. Outlook
8. Disclosure Gaps

### Setup & Usage
```bash
# Ensure vector DB is populated
python src/index_for_rag.py

# Set OpenAI API key
export OPENAI_API_KEY="your-key-here"

# Run dashboard API
python src/rag_dashboard.py

# Generate dashboard
curl -X POST "http://localhost:8002/dashboard/rag" \
  -H "Content-Type: application/json" \
  -d '{"company_id": "anthropic", "top_k": 10}'
```

### Configuration
- Model: `gpt-4o-mini`
- Temperature: 0.1 (for consistency)
- Top-k chunks: 10 (default)
- Max tokens: 2500

---

## Testing & Validation

### Test All Labs
```bash
# Lab 4: Test vector search
curl -X POST "http://localhost:8001/rag/search" \
  -d '{"query": "AI safety", "n_results": 5}'

# Lab 5: Check structured extraction
ls -la data/structured/*.json

# Lab 6: Validate payloads
python src/structured_pipeline.py

# Lab 7: Generate dashboards for multiple companies
for company in anthropic databricks cohere openevidence glean; do
  echo "Testing $company..."
  curl -X POST "http://localhost:8002/dashboard/rag" \
    -d "{\"company_id\": \"$company\"}" | jq -r '.chunks_used'
done
```

### Expected Results
- Lab 4: Returns relevant text chunks with metadata
- Lab 5: Creates JSON files with structured company data
- Lab 6: All payloads pass validation
- Lab 7: Dashboards with 8 sections, using 3-10 chunks per company

---

## Data Flow

```
Raw HTML/Text (data/raw/)
        ↓
    Lab 4: Chunking & Embedding
        ↓
    Vector DB (data/vector_db/)
        ↓
    Lab 7: RAG Dashboard
        ↓
    8-Section Markdown Report

Parallel Path:
Raw HTML/Text (data/raw/)
        ↓
    Lab 5: Structured Extraction
        ↓
    JSON Files (data/structured/)
        ↓
    Lab 6: Payload Assembly
        ↓
    Validated Payloads (data/payloads/)
```

---

## Troubleshooting

### Common Issues

1. **OpenAI API Key Error**
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

2. **Vector DB Not Found**
   ```bash
   python src/index_for_rag.py  # Rebuild vector DB
   ```

3. **Port Already in Use**
   ```bash
   lsof -i :8001  # or :8002
   kill -9 <PID>
   ```

4. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

## Performance Metrics

| Lab | Companies Processed | Processing Time | Success Rate |
|-----|-------------------|-----------------|--------------|
| Lab 4 | 30 | ~5 min | 100% |
| Lab 5 | 5 | ~3 min | 100% |
| Lab 6 | 5 | <1 min | 100% |
| Lab 7 | 5 tested | ~10 sec/dashboard | 100% |

---

## Dependencies

```txt
chromadb==0.4.22
sentence-transformers==2.3.1
fastapi==0.109.0
uvicorn==0.27.0
tiktoken==0.5.2
openai==1.12.0
instructor==0.5.2
pydantic==2.5.3
python-dotenv==1.0.0
```

---

## Author
- **Name:** Kundana
- **Branch:** kundana
- **Labs Completed:** 4, 5, 6, 7
- **Date:** November 2025

---

After successful implementation:
- ✅ Companies scraped into `data/raw/<company_id>/initial/...`
- ✅ Each page type has both `.html` (raw) and `.txt` (clean text) files
- ✅ Each page has corresponding `_metadata.json` with required fields
- ✅ Summary file generated at `data/raw/scrape_summary_initial_<timestamp>.json`
- ✅ All 5 page types attempted for each company (homepage, about, product, careers, blog)
