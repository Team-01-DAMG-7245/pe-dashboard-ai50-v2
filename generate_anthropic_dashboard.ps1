# Generate Anthropic Dashboard with proper formatting
# This script generates a properly formatted dashboard for Anthropic
# API key is loaded from .env file

$env:KMP_DUPLICATE_LIB_OK = "TRUE"

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] .env file not found!"
    Write-Host "Please create a .env file with your OPENAI_API_KEY:"
    Write-Host "  OPENAI_API_KEY=your-api-key-here"
    exit 1
}

Write-Host "Generating Anthropic Dashboard..."
Write-Host ""

# Check if API is running
try {
    $health = Invoke-RestMethod -Uri http://localhost:8002/health -TimeoutSec 5
    Write-Host "[OK] API Server is running"
} catch {
    Write-Host "[ERROR] API Server is not running. Please start it first:"
    Write-Host "  .\start_api_server.ps1"
    exit 1
}

# Generate dashboard
$body = @{
    company_id = "anthropic"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8002/dashboard/structured" -Method Post -Body $body -ContentType "application/json"
    
    # Create output directory
    $outputDir = "src\lab9\evaluation_output"
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    # Generate timestamp
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    
    # Create properly formatted markdown
    $markdown = @"
# Structured Dashboard: ANTHROPIC

**Generated:** $timestamp  
**Source:** Structured Payload (data/payloads/anthropic.json)

---

$($response.dashboard)
"@
    
    # Save to file
    $outputFile = "$outputDir\anthropic_structured_final.md"
    $markdown | Out-File -FilePath $outputFile -Encoding UTF8
    
    Write-Host ""
    Write-Host "=========================================="
    Write-Host "[SUCCESS] Dashboard generated!"
    Write-Host "=========================================="
    Write-Host "Output file: $outputFile"
    Write-Host ""
    Write-Host "Preview:"
    Write-Host "=========================================="
    $markdown
    Write-Host "=========================================="
    
} catch {
    Write-Host "[ERROR] Failed to generate dashboard: $_"
    exit 1
}

