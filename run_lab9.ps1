# Run Lab 9 Evaluation
# Ensure the API server is running first (start_api_server.ps1)
# API key is loaded from .env file

$env:KMP_DUPLICATE_LIB_OK = "TRUE"  # Fix OpenMP warning

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] .env file not found!"
    Write-Host "Please create a .env file with your OPENAI_API_KEY:"
    Write-Host "  OPENAI_API_KEY=your-api-key-here"
    exit 1
}

Write-Host "Running Lab 9 Evaluation..."
Write-Host "Make sure the API server is running at http://localhost:8002"
Write-Host ""

python src\lab9\evaluate_comparison.py

