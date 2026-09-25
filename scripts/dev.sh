#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
[[ -f .env ]] || { echo 'Run ./scripts/setup.sh first.' >&2; exit 1; }
docker compose --project-directory "$ROOT" -f docker/docker-compose.yml up --build -d
echo 'Development services started: API http://localhost:8000/docs; dashboard http://localhost:8501'
