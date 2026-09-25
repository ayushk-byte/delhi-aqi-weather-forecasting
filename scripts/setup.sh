#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
fail() { echo "ERROR: $*" >&2; exit 1; }
for cmd in docker node python git; do command -v "$cmd" >/dev/null 2>&1 || fail "$cmd is required and was not found in PATH."; done
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required (docker compose)."
docker info >/dev/null 2>&1 || fail "Docker daemon is not running or is inaccessible. Start Docker and rerun setup."
python -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' || fail "Python 3.10 or newer is required."
node -e 'process.exit(Number(process.versions.node.split(".")[0]) < 18)' || fail "Node.js 18+ is required (kept for frontend tooling compatibility)."
if [[ ! -f .env ]]; then cp .env.example .env; echo "Created .env from .env.example. Configure OPENAQ_API_KEY then rerun setup."; fi
set -a; source .env; set +a
[[ -n "${OPENAQ_API_KEY:-}" && "$OPENAQ_API_KEY" != replace-* ]] || fail "Set a valid OPENAQ_API_KEY in .env. See README > Quick Start."
python -m venv .venv
if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; PIP=.venv/bin/pip; else PY=.venv/Scripts/python.exe; PIP=.venv/Scripts/pip.exe; fi
"$PIP" install --upgrade pip
"$PIP" install -r requirements.txt -r requirements-dev.txt
"$PIP" install -e . --no-deps
docker compose --project-directory "$ROOT" -f docker/docker-compose.yml up -d postgres redis
for attempt in $(seq 1 30); do
  if "$PY" -c 'import socket; socket.create_connection(("127.0.0.1",5432),1).close(); socket.create_connection(("127.0.0.1",6379),1).close()' 2>/dev/null; then break; fi
  [[ "$attempt" -lt 30 ]] || fail "PostgreSQL/Redis did not become reachable. Inspect: docker compose --project-directory . -f docker/docker-compose.yml logs postgres redis"
  sleep 2
done
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:${POSTGRES_PASSWORD:-postgres}@127.0.0.1:5432/aqi}"
"$PY" -m src.storage.postgres
echo "Checking live providers and ingesting real observations (mock providers are not used)..."
AQI_PROVIDER=openaq WEATHER_PROVIDER=open_meteo "$PY" -m src.pipelines.ingest_pipeline --aqi-provider openaq --weather-provider open_meteo
COUNTS=$("$PY" -c 'import json; from src.storage.postgres import observation_counts; print(json.dumps(observation_counts()))')
AQI_COUNT=$(printf '%s' "$COUNTS" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["air_quality"])')
WEATHER_COUNT=$(printf '%s' "$COUNTS" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["weather"])')
[[ "$AQI_COUNT" -gt 0 && "$WEATHER_COUNT" -gt 0 ]] || fail "Initial live observations were not stored in PostgreSQL. Check provider connectivity and rerun."
echo "Setup complete. Start services with ./scripts/dev.sh"
echo "Live database observations — Air quality: $AQI_COUNT; Weather: $WEATHER_COUNT"
echo "After starting services, verify: ./scripts/health-check.sh"
