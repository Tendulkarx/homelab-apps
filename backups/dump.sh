#!/usr/bin/env bash
# Nightly dumps of the databases and app data on this host, into /opt/backups/<date>/ (14 days
# kept). Each part runs only where its container runs: Postgres, SQL Server and Oracle on
# prdsrv2; n8n and Paperless on prdsrv1. Run by the systemd timer db-dumps.timer at 01:30,
# before the 02:30 VM backup, so each night's dumps are also inside that backup.
# By hand: sudo /opt/docker/backups/dump.sh
#
#   postgres/<db>.dump   pg_dump custom format: pg_restore -d <db> <file>
#   postgres/globals.sql roles and their passwords: psql -f globals.sql
#   sqlserver/<db>.bak.gz  BACKUP DATABASE ... COPY_ONLY: gunzip, then RESTORE DATABASE
#   oracle/freepdb1.dmp.gz Data Pump full export of FREEPDB1: gunzip, then impdp
#   n8n/                 its SQLite database (online copy) and config (holds the key for
#                        stored credentials)
#   paperless.tar.gz     document_exporter output: document_importer restores it
#
# One part failing does not stop the others; the exit code is then 1 and the heartbeat is
# not sent, so Uptime Kuma reports it. Passwords are read inside each container from its own
# environment and never pass through this script's arguments.
set -uo pipefail

ROOT=/opt/backups
KEEP_DAYS=14
DAY=$(date +%F)
OUT="$ROOT/$DAY"
failed=()

log() { echo "$(date +%T) $*"; }
fail() { log "FAILED: $1"; failed+=("$1"); }

here() { [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" = true ]; }

umask 077
mkdir -p "$OUT"

postgres() {
  mkdir -p "$OUT/postgres"
  docker exec postgres pg_dumpall -U postgres --globals-only > "$OUT/postgres/globals.sql" || return 1
  local db dbs
  dbs=$(docker exec postgres psql -U postgres -Atc \
    "select datname from pg_database where not datistemplate and datname <> 'postgres'") || return 1
  [ -n "$dbs" ] || return 1
  for db in $dbs; do
    docker exec postgres pg_dump -U postgres -Fc "$db" > "$OUT/postgres/$db.dump" || return 1
    log "postgres $db $(du -h "$OUT/postgres/$db.dump" | cut -f1)"
  done
}

sqlserver() {
  mkdir -p "$OUT/sqlserver"
  local sql='/opt/mssql-tools18/bin/sqlcmd -C -b -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -h -1 -W'
  local db dbs
  # Every database but tempdb: master holds the logins, msdb the agent jobs.
  dbs=$(docker exec sqlserver bash -c "$sql -Q \"set nocount on; select name from sys.databases where name <> 'tempdb' and state = 0\"") || return 1
  [ -n "$dbs" ] || return 1
  for db in $dbs; do
    docker exec sqlserver bash -c "mkdir -p /var/opt/mssql/backup && $sql -Q \"BACKUP DATABASE [$db] TO DISK = '/var/opt/mssql/backup/$db.bak' WITH COPY_ONLY, INIT\"" > /dev/null || return 1
    docker exec sqlserver cat "/var/opt/mssql/backup/$db.bak" | gzip > "$OUT/sqlserver/$db.bak.gz" || return 1
    docker exec sqlserver rm -f "/var/opt/mssql/backup/$db.bak"
    log "sqlserver $db $(du -h "$OUT/sqlserver/$db.bak.gz" | cut -f1)"
  done
}

oracle() {
  # Data Pump writes on the server side, into DATA_PUMP_DIR; the file is streamed out and removed.
  mkdir -p "$OUT/oracle"
  local dir
  dir=$(printf 'set heading off feedback off pagesize 0\nalter session set container=FREEPDB1;\nselect directory_path from dba_directories where directory_name = %s;\n' "'DATA_PUMP_DIR'" |
    docker exec -i oracle sqlplus -s / as sysdba | tr -d '[:space:]')
  [ -n "$dir" ] || return 1
  docker exec oracle bash -c 'rm -f '"$dir"'/nightly.dmp; printf "userid=\"system/%s@localhost:1521/FREEPDB1\"\n" "$ORACLE_PWD" > /tmp/expdp.par; chmod 600 /tmp/expdp.par
    expdp parfile=/tmp/expdp.par full=y directory=DATA_PUMP_DIR dumpfile=nightly.dmp logfile=nightly.log > /dev/null 2>&1; rc=$?; rm -f /tmp/expdp.par; exit $rc' || {
    docker exec oracle tail -5 "$dir/nightly.log"; return 1; }
  docker exec oracle cat "$dir/nightly.dmp" | gzip > "$OUT/oracle/freepdb1.dmp.gz" || return 1
  docker exec oracle cat "$dir/nightly.log" > "$OUT/oracle/freepdb1.log"
  docker exec oracle rm -f "$dir/nightly.dmp"
  log "oracle FREEPDB1 $(du -h "$OUT/oracle/freepdb1.dmp.gz" | cut -f1)"
}

n8n() {
  mkdir -p "$OUT/n8n"
  python3 - "$OUT/n8n/database.sqlite" <<'PY' || return 1
import sqlite3, sys
src = sqlite3.connect("file:/opt/docker/n8n/data/database.sqlite?mode=ro", uri=True)
dst = sqlite3.connect(sys.argv[1])
src.backup(dst)
dst.close()
PY
  cp /opt/docker/n8n/data/config "$OUT/n8n/config"
  log "n8n $(du -sh "$OUT/n8n" | cut -f1)"
}

paperless() {
  docker exec paperless-webserver document_exporter ../export --delete --no-progress-bar > /dev/null || return 1
  tar -C /opt/docker/paperless -czf "$OUT/paperless.tar.gz" export || return 1
  log "paperless $(du -h "$OUT/paperless.tar.gz" | cut -f1)"
}

# part:container that must be running on this host for the part to apply
ran=0
for pc in postgres:postgres sqlserver:sqlserver oracle:oracle n8n:n8n paperless:paperless-webserver; do
  here "${pc#*:}" || continue
  ran=$((ran + 1))
  "${pc%%:*}" || fail "${pc%%:*}"
done
[ "$ran" -gt 0 ] || fail "nothing to back up on $(hostname)"

find "$ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} +
log "total $(du -sh "$OUT" | cut -f1) in $OUT"

if [ ${#failed[@]} -gt 0 ]; then
  log "failed parts: ${failed[*]}"
  exit 1
fi
# Uptime Kuma push monitor "Database dumps"; the URL lives in /etc/default/db-dumps (not in git)
if [ -n "${HEARTBEAT_URL:-}" ]; then
  curl -fsS -m 10 -o /dev/null "$HEARTBEAT_URL?status=up&msg=OK" || log "heartbeat not sent"
fi
