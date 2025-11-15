# PowerShell script to approve/reject HITL requests
# Usage: .\approve_hitl.ps1 -RunId "anthropic_20251115_114103" -Approved -Reviewer "admin" -Notes "Approved"

param(
    [Parameter(Mandatory=$true)]
    [string]$RunId,
    
    [Parameter(Mandatory=$false)]
    [switch]$Approved,
    
    [Parameter(Mandatory=$false)]
    [switch]$Rejected,
    
    [Parameter(Mandatory=$false)]
    [string]$Reviewer = "admin",
    
    [Parameter(Mandatory=$false)]
    [string]$Notes = "",
    
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "http://localhost:8003"
)

# Determine action
if ($Approved) {
    $action = "approve"
    $approved = $true
} elseif ($Rejected) {
    $action = "reject"
    $approved = $false
} else {
    Write-Host "Error: Must specify either -Approved or -Rejected" -ForegroundColor Red
    exit 1
}

# Prepare request body
$body = @{
    approved = $approved
    reviewer = $Reviewer
    notes = $Notes
} | ConvertTo-Json

# Make request
$url = "$BaseUrl/hitl/$action/$RunId"
Write-Host "Sending $action request to: $url" -ForegroundColor Cyan
Write-Host "Body: $body" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json"
    Write-Host "`n✅ Success!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 10)
} catch {
    Write-Host "`n❌ Error: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Yellow
    }
}

