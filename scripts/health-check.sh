#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
URL="${API_BASE_URL:-http://localhost:8000/api/system/health}"
command -v curl >/dev/null || { echo 'curl is required.' >&2; exit 1; }
curl --fail --silent --show-error "$URL" | python -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps(d, indent=2)); print("\nHuman status: " + d["status"].upper()); [print(f"{k}: {v}") for k,v in d.items() if k in ("database","redis","weather_api","air_quality_api","forecast_model")]; sys.exit(0 if d["status"] == "healthy" else 1)'
