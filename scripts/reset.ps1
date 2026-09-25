$ErrorActionPreference='Stop'; Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
Write-Warning 'This deletes the local PostgreSQL volume and all local date-partitioned observations.'
if ((Read-Host 'Type DELETE to continue') -cne 'DELETE') { Write-Host 'Reset cancelled.'; exit 1 }
docker compose --project-directory (Get-Location).Path -f docker/docker-compose.yml down -v
if ($LASTEXITCODE -ne 0) { throw 'Could not stop services and remove database volume.' }
foreach ($path in @('data/raw','data/processed','data/features')) { if (Test-Path $path) { Remove-Item -LiteralPath $path -Recurse -Force } }
Write-Host 'Local data removed. Rebuild with .\scripts\setup.ps1'
