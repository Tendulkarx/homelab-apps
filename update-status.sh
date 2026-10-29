#!/usr/bin/env bash
# Write updates.json for the Homarr Updates card: check-updates.sh --json over every app's pinned
# version on GitHub (this host checks out only its own folders, so it reads them from git), into
# /opt/status, which Caddy serves to Homarr only (http://caddy:8099, not published). Run every six
# hours on prdsrv1 by the update-status timer (proxmox-lab, role update_status); by hand:
#   /opt/docker/update-status.sh
set -euo pipefail
repo=$(cd "$(dirname "$0")" && pwd)
out=${UPDATE_STATUS_FILE:-/opt/status/updates.json}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

git -C "$repo" fetch -q origin main
git -C "$repo" archive origin/main | tar -x -C "$tmp"
"$tmp/check-updates.sh" --json >"$tmp/updates.json" 2>/dev/null
jq -e '.checked and (.images | length > 0)' "$tmp/updates.json" >/dev/null
install -m 0644 "$tmp/updates.json" "$out.new" && mv "$out.new" "$out"
jq -r '"\(.behind) behind, \(.majors) with a new major, \(.unreadable) unreadable"' "$out"
