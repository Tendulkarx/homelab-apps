#!/usr/bin/env bash
# The only command n8n's SSH key may run (forced command in ~turbx/.ssh/authorized_keys).
# By hand: ./run.sh [run|check|import-sheet|migrate] [options]; no arguments means a normal run.
# Each run writes logs/property_search_<time>.log and keeps its container so Dozzle can show it;
# containers go after 14 days, log files after 90. logs/ is 1777 like /tmp: the app runs as UID
# 10001 (the 1Password CLI needs that account) and turbx, owning the folder, can still delete.
set -euo pipefail
cd "$(dirname "$0")"
stamp=$(date +%Y-%m-%d_%H-%M-%S)
mkdir -p logs && chmod 1777 logs
docker container prune --force --filter label=com.docker.compose.project=property-search --filter until=336h >/dev/null
find logs -name 'property_search_*.log*' -mtime +90 -delete
exec docker compose run --name "property-search_$stamp" --no-TTY property-search \
  "${@:-run}" --log-file "/logs/property_search_$stamp.log"
