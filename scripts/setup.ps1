$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
function Require-Command($name) { if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { throw "$name is required and was not found in PATH." } }
foreach ($name in @('docker', 'node', 'python', 'git')) { Require-Command $name }
docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose v2 is required.' }
docker info | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker daemon is not running or is inaccessible. Start Docker and rerun setup.' }
python -c "import sys; raise SystemExit(sys.version_info < (3, 10))"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 or newer is required.' }
node -e "process.exitCode = Number(process.versions.node.split('.')[0] < 18)"
if ($LASTEXITCODE -ne 0) { throw 'Node.js 18+ is required (kept for frontend tooling compatibility).' }
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env'; Write-Host 'Created .env. Configure OPENAQ_API_KEY then rerun setup.' }
$envLines = Get-Content '.env' | Where-Object { $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*=' -and $_ -notmatch '^\s*#' }
foreach ($line in $envLines) { $parts = $line -split '=', 2; [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process') }
if (-not $env:OPENAQ_API_KEY -or $env:OPENAQ_API_KEY -like 'replace-*') { throw 'Set a valid OPENAQ_API_KEY in .env. See README > Quick Start.' }
python -m venv .venv
$pythonExe = Join-Path $root '.venv\Scripts\python.exe'
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r requirements.txt -r requirements-dev.txt
& $pythonExe -m pip install -e . --no-deps
docker compose --project-directory $root -f docker/docker-compose.yml up -d postgres redis
if ($LASTEXITCODE -ne 0) { throw 'Could not start PostgreSQL and Redis. Check that Docker is running.' }
$ready = $false
for ($i = 0; $i -lt 30; $i++) { Start-Sleep -Seconds 2; try { $tcp = [Net.Sockets.TcpClient]::new(); $tcp.Connect('127.0.0.1',5432); $tcp.Close(); $tcp = [Net.Sockets.TcpClient]::new(); $tcp.Connect('127.0.0.1',6379); $tcp.Close(); $ready = $true; break } catch {} }
if (-not $ready) { throw 'PostgreSQL/Redis did not become reachable. Inspect docker compose logs.' }
$password = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { 'postgres' }
if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "postgresql://postgres:$password@127.0.0.1:5432/aqi" }
& $pythonExe -m src.storage.postgres
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
Write-Host 'Checking live providers and ingesting real observations (mock providers are not used)...'
$env:AQI_PROVIDER = 'openaq'; $env:WEATHER_PROVIDER = 'open_meteo'
& $pythonExe -m src.pipelines.ingest_pipeline --aqi-provider openaq --weather-provider open_meteo
if ($LASTEXITCODE -ne 0) { throw 'Live ingestion failed; no fake fallback was used.' }
$countsJson = & $pythonExe -c 'import json; from src.storage.postgres import observation_counts; print(json.dumps(observation_counts()))'
if ($LASTEXITCODE -ne 0) { throw 'Could not verify database observations.' }
$counts = $countsJson | ConvertFrom-Json
$aqiCount = $counts.air_quality; $weatherCount = $counts.weather
if ($aqiCount -lt 1 -or $weatherCount -lt 1) { throw 'Initial ingestion did not store live observations in the database.' }
Write-Host 'Setup complete. Start services with .\scripts\dev.ps1'
Write-Host "Live database observations — Air quality: $aqiCount; Weather: $weatherCount"
Write-Host 'After starting services, verify: .\scripts\health-check.ps1'
