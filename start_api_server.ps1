# Start Lab 7 & 8 API Server
# This will start the FastAPI server with Swagger UI
# API key is loaded from .env file

$env:PYTHONPATH = "src"
$env:KMP_DUPLICATE_LIB_OK = "TRUE"  # Fix OpenMP warning

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] .env file not found!"
    Write-Host "Please create a .env file with your OPENAI_API_KEY:"
    Write-Host "  OPENAI_API_KEY=your-api-key-here"
    exit 1
}

Write-Host "Starting Lab 7 & 8 API Server..."
Write-Host "Swagger UI will be available at: http://localhost:8002/docs"
Write-Host "Health Check: http://localhost:8002/health"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server"
Write-Host ""

python src\lab7\rag_dashboard.py

