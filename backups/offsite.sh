#!/usr/bin/env bash
# Off-site tier 1: today's dumps (dump.sh) to Google Drive, encrypted by rclone crypt before
# they leave prdsrv2; 30 days kept, about 1 GB of the free 15 GB. Run by db-offsite.timer at
# 03:00. By hand: sudo /opt/docker/backups/offsite.sh
#
# The remote `offsite:` (crypt over Drive folder homelab-offsite, drive.file scope, so rclone
# sees only what it made) is in /root/.config/rclone/rclone.conf, written by setup-offsite.sh
# from 1Password item prdsrv2-rclone. Without those keys the copies cannot be read: they are
# in 1Password only.
#
# Restore: sudo rclone copy offsite:daily/<date> /tmp/restore
set -euo pipefail

DAY=${1:-$(date +%F)}
SRC=/opt/backups/$DAY
KEEP=30d

[ -d "$SRC" ] || { echo "No dumps for $DAY in $SRC"; exit 1; }

# The dev database is a copy of prod for trying changes: rebuildable, so not sent.
rclone copy "$SRC" "offsite:daily/$DAY" --exclude postgres/property_search_dev.dump --stats-one-line -v 2>&1 | tail -2
rclone delete offsite:daily --min-age "$KEEP"
rclone rmdirs offsite:daily --leave-root
echo "offsite: $(rclone size offsite:daily --json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["count"], "files,", round(d["bytes"]/1048576), "MB")')"

if [ -n "${OFFSITE_HEARTBEAT_URL:-}" ]; then
  curl -fsS -m 10 -o /dev/null "$OFFSITE_HEARTBEAT_URL?status=up&msg=OK" || echo "heartbeat not sent"
fi
