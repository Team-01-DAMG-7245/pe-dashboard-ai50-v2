# Start HITL Approval Server (Lab 18)
# This starts the FastAPI server for HTTP-based HITL approvals

$env:PYTHONPATH = "src"

Write-Host "Starting HITL Approval Server..."
Write-Host "Server will be available at: http://localhost:8003"
Write-Host "API Documentation: http://localhost:8003/docs"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server"
Write-Host ""

python src\workflows\hitl_handler.py

