$ErrorActionPreference='Stop'; Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
docker compose --project-directory (Get-Location).Path -f docker/docker-compose.yml down
if ($LASTEXITCODE -ne 0) { throw 'Failed to stop services.' }
