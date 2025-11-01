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

After successful implementation:
- ✅ Companies scraped into `data/raw/<company_id>/initial/...`
- ✅ Each page type has both `.html` (raw) and `.txt` (clean text) files
- ✅ Each page has corresponding `_metadata.json` with required fields
- ✅ Summary file generated at `data/raw/scrape_summary_initial_<timestamp>.json`
- ✅ All 5 page types attempted for each company (homepage, about, product, careers, blog)