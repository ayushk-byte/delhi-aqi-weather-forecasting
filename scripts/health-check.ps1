$ErrorActionPreference='Stop'
$url = if ($env:API_BASE_URL) { "$($env:API_BASE_URL.TrimEnd('/'))/api/system/health" } else { 'http://localhost:8000/api/system/health' }
$health = Invoke-RestMethod -Uri $url -TimeoutSec 40
$health | ConvertTo-Json -Depth 8
Write-Host "`nHuman status: $($health.status.ToUpper())"
foreach ($key in @('database','redis','weather_api','air_quality_api','forecast_model')) { Write-Host "${key}: $($health.$key)" }
if ($health.status -ne 'healthy') { exit 1 }
