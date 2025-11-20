# PowerShell script to check HITL status
# Usage: .\check_hitl_status.ps1 -RunId "anthropic_20251115_114103"
# Or: .\check_hitl_status.ps1 (to list all pending)

param(
    [Parameter(Mandatory=$false)]
    [string]$RunId,
    
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "http://localhost:8003"
)

if ($RunId) {
    # Check specific run ID
    $url = "$BaseUrl/hitl/status/$RunId"
    Write-Host "Checking status for: $RunId" -ForegroundColor Cyan
    Write-Host "URL: $url`n" -ForegroundColor Gray
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get
        Write-Host ($response | ConvertTo-Json -Depth 10)
    } catch {
        Write-Host "❌ Error: $_" -ForegroundColor Red
        if ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host "No pending approval found for run_id: $RunId" -ForegroundColor Yellow
        }
    }
} else {
    # List all pending approvals
    $url = "$BaseUrl/hitl/pending"
    Write-Host "Listing all pending approvals..." -ForegroundColor Cyan
    Write-Host "URL: $url`n" -ForegroundColor Gray
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get
        Write-Host "Pending Count: $($response.pending_count)" -ForegroundColor Green
        Write-Host "`nPending Approvals:" -ForegroundColor Yellow
        Write-Host ($response.pending_approvals | ConvertTo-Json -Depth 10)
    } catch {
        Write-Host "❌ Error: $_" -ForegroundColor Red
    }
}

