# Run All Labs - Quick Reference

## Prerequisites

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Set environment variables
$env:PYTHONPATH = ".;src"
$env:OPENAI_API_KEY = (Get-Content .env | Select-String "OPENAI_API_KEY" | ForEach-Object { $_.Line -replace '.*=', '' }).Trim()
```

## Lab 4: Vector DB & RAG Index

```powershell
python src\lab4\index_for_rag_all.py
```

**Checkpoint:** Vector DB should have 96+ chunks indexed.

## Lab 5: Structured Extraction

```powershell
python src\lab5\structured_extraction.py
```

**Checkpoint:** At least 5 companies with structured data in `data/structured/`.

## Lab 6: Payload Assembly & Validation

```powershell
python src\lab6\test_validation.py
```

**Checkpoint:** All 5 payloads validate successfully.

## Lab 7 & 8: Dashboard API (Combined)

```powershell
python src\lab7\rag_dashboard.py
```

**Endpoints:**
- Lab 7 RAG: `POST http://localhost:8002/dashboard/rag`
- Lab 8 Structured: `POST http://localhost:8002/dashboard/structured`
- Swagger UI: http://localhost:8002/docs

**Test Lab 7:**
```powershell
$body = @{company_id="anthropic"; top_k=10} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8002/dashboard/rag" -Method Post -Body $body -ContentType "application/json"
```

**Test Lab 8:**
```powershell
$body = @{company_id="anthropic"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8002/dashboard/structured" -Method Post -Body $body -ContentType "application/json"
```

## Lab 9: Evaluation & Comparison

```powershell
python src\lab9\evaluate_comparison.py
```

**Output:** Dashboards saved in `evaluation_output/` for rubric scoring in `EVAL.md`.

## Complete Sequence

```powershell
# 1. Setup
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = ".;src"
$env:OPENAI_API_KEY = (Get-Content .env | Select-String "OPENAI_API_KEY" | ForEach-Object { $_.Line -replace '.*=', '' }).Trim()

# 2. Lab 4
python src\lab4\index_for_rag_all.py

# 3. Lab 5
python src\lab5\structured_extraction.py

# 4. Lab 6
python src\lab6\test_validation.py

# 5. Lab 7/8 (in separate terminal)
python src\lab7\rag_dashboard.py

# 6. Lab 9 (after API is running)
python src\lab9\evaluate_comparison.py
```

