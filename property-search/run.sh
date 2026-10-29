#!/usr/bin/env bash
# The only command n8n's SSH key may run (forced command in the admin user's ~/.ssh/authorized_keys).
# By hand: ./run.sh [run|check|import-sheet|migrate] [options]; no arguments means a normal run.
# Each run writes logs/property_search_<time>.log (kept 90 days). A run that succeeds removes its
# container, so the Homarr and Dozzle container lists show only failed runs ("Exited"); those stay
# until the next successful run, which removes them too. The exit status goes back to n8n. logs/ is 1777 like /tmp: the app runs as UID
# 10001 and the admin user, owning the folder, can still delete.
#
# Before each run it brings /opt/docker up to date when the only changes waiting on GitHub are
# property-search's (or in folders or top-level files this host does not run), so merging the
# release PR, or a change to searches.json, is the whole deploy. Changes to anything else this
# host runs are left for a person to pull, and the run goes ahead on what is here.
set -euo pipefail

fast_forward_homelab_apps() {
  local repo changed path folder
  repo=$(git rev-parse --show-toplevel) || return 0
  if ! timeout 60 git -C "$repo" fetch --quiet origin main; then
    echo "run.sh: could not fetch homelab-apps; running what is here" >&2
    return 0
  fi
  changed=$(git -C "$repo" diff --name-only HEAD origin/main) || return 0
  [ -n "$changed" ] || return 0
  while IFS= read -r path; do
    folder=${path%%/*}
    [ "$folder" = "$path" ] && continue # a top-level file: docs and Mac scripts, nothing runs it
    [ "$folder" = property-search ] && continue
    if [ -d "$repo/$folder" ]; then # checked out here, so this host runs it
      echo "run.sh: homelab-apps has changes to $folder waiting; pull them by hand" \
        "(cd /opt/docker && git pull). Running what is here." >&2
      return 0
    fi
  done <<<"$changed"
  if git -C "$repo" merge --ff-only --quiet origin/main; then
    echo "run.sh: homelab-apps updated to $(git -C "$repo" rev-parse --short HEAD)" >&2
  else
    echo "run.sh: homelab-apps could not fast-forward (local edits?); running what is here" >&2
  fi
}

main() {
  cd "$(dirname "$0")"
  fast_forward_homelab_apps
  stamp=$(date +%Y-%m-%d_%H-%M-%S)
  mkdir -p logs && chmod 1777 logs
  find logs -name 'property_search_*.log*' -mtime +90 -delete
  local rc=0
  docker compose run --name "property-search_$stamp" --no-TTY property-search \
    "${@:-run}" --log-file "/logs/property_search_$stamp.log" || rc=$?
  if [ "$rc" -eq 0 ]; then
    docker container prune --force --filter label=com.docker.compose.project=property-search >/dev/null
  fi
  return "$rc"
}

# Read to the end before running: the update above may replace this file.
main "$@"; exit
