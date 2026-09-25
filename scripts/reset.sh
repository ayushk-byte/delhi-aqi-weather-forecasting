#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
echo 'WARNING: this deletes the local PostgreSQL volume and all local date-partitioned observations.'
read -r -p 'Type DELETE to continue: ' answer
[[ "$answer" == DELETE ]] || { echo 'Reset cancelled.'; exit 1; }
docker compose --project-directory "$ROOT" -f docker/docker-compose.yml down -v
rm -rf data/raw data/processed data/features
echo 'Local data removed. Rebuild with ./scripts/setup.sh'
