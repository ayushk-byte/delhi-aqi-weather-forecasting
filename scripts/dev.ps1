$ErrorActionPreference='Stop'; $root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path; Set-Location $root
if (-not (Test-Path '.env')) { throw 'Run .\scripts\setup.ps1 first.' }
docker compose -p delhi-aqi-weather-forecasting -f docker/docker-compose.yml up --build -d
if ($LASTEXITCODE -ne 0) { throw 'Could not start development services.' }
Write-Host 'API http://localhost:8000/docs; dashboard http://localhost:8501'
