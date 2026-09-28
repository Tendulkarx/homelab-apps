#!/usr/bin/env bash
# The only command n8n's SSH key may run (forced command in ~turbx/.ssh/authorized_keys).
# By hand: ./run.sh [run|check|import-sheet|migrate] [options]; no arguments means a normal run.
set -euo pipefail
cd "$(dirname "$0")"
exec docker compose run --rm --no-TTY property-search "${@:-run}"
