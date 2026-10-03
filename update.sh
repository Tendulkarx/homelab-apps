#!/usr/bin/env bash
# Update the apps to the newest release in their current major version, the way Arcane's
# update button did, but with the new version recorded in git. Run on the Mac:
#
#   ./update.sh                 every app with an update; shows the list and asks once
#   ./update.sh n8n caddy       only these folders
#   ./update.sh homarr=v2.0.0   an exact version (any version that exists, older or newer)
#   ./update.sh --major homarr  the newest release, even a new major version
#   ./update.sh --dry-run       show what would change, change nothing
#   ./update.sh --no-backup     skip the VM backups (they take a few minutes per host)
#   ./update.sh --yes           do not ask (for a non-interactive shell)
#
# Steps: bump the pinned tags, commit and push, back up each affected host (proxmox-lab
# `make backup`), then on each host `git pull` and recreate only the updated apps, Caddy
# last. Without --major or name=version it stays within each app's major version; a major
# jump is marked MAJOR in the list (read its upgrade notes first). Rolling back is `git revert` of the update commit, then ./update.sh's
# last step by hand (see README, "Updating an app").
set -euo pipefail
cd "$(dirname "$0")"
source ./check-updates.sh
LAB=${PROXMOX_LAB:-../proxmox-lab}

dry=false backup=true yes=false major=false only=() pins=()
for a in "$@"; do
  case $a in
    --dry-run) dry=true ;;
    --no-backup) backup=false ;;
    --yes|-y) yes=true ;;
    --major) major=true ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    -*) echo "Unknown option $a" >&2; exit 2 ;;
    *=*) pins+=("$a"); only+=("${a%%=*}") ;;
    *) only+=("${a%/}") ;;
  esac
done

[ -z "$(git status --porcelain)" ] || { echo "homelab-apps has uncommitted changes; commit or stash them first." >&2; exit 1; }
git pull -q --ff-only

# 1. What can be updated: file, folder, old ref, new ref
changes=()
files=(*/docker-compose.yml caddy/Dockerfile)
for f in "${files[@]}"; do
  folder=${f%%/*}
  refs=$(if [ "$f" = caddy/Dockerfile ]; then awk '/^FROM /{print $2}' "$f"; else awk '/^[[:space:]]*image:/{print $2}' "$f" | tr -d '"'; fi)
  for ref in $refs; do
    base=${ref%:*}; base=${base##*/}; cur=${ref##*:}
    [ ${#only[@]} -eq 0 ] || [[ " ${only[*]} " == *" $folder "* ]] || [[ " ${only[*]} " == *" $base "* ]] || continue
    want=""
    # name=version matches the image; the folder name too when the folder has just one image
    for p in ${pins[@]+"${pins[@]}"}; do
      { [ "${p%%=*}" = "$base" ] || { [ "${p%%=*}" = "$folder" ] && [ "$(wc -w <<<"$refs")" -eq 1 ]; }; } && want=${p#*=}
    done
    if [ -n "$want" ]; then
      # Keep a suffix such as -builder or -ubuntu-24.04 that the current tag carries
      suffix=$(sed -E 's/^[^0-9]*[0-9]+([.][0-9]+)*//' <<<"$cur"); [[ "$want" == *"$suffix" ]] || want="$want$suffix"
      versions "$ref" | grep -qx -- "$want" || { echo "$base: no release tagged $want (./check-updates.sh lists them)" >&2; exit 1; }
      new=$want; [ "$new" = "$cur" ] && new=""
    elif $major; then
      new=$(versions "$ref" | tail -1 || true)
      [ -n "$new" ] && [ "$(printf '%s\n%s\n' "$cur" "$new" | sort -V | tail -1)" = "$new" ] && [ "$new" != "$cur" ] || new=""
    else
      new=$(newer_same_major "$ref" || true)
    fi
    [ -n "$new" ] && changes+=("$f|$folder|$ref|${ref%:*}:$new")
  done
done
if [ ${#changes[@]} -eq 0 ]; then echo "Everything is up to date (majors, if any: ./check-updates.sh)."; exit 0; fi

echo "Changes:"
for c in "${changes[@]}"; do
  IFS='|' read -r f folder old new <<<"$c"
  m1=$(grep -oE '^[^0-9]*[0-9]+' <<<"${old##*:}"); m2=$(grep -oE '^[^0-9]*[0-9]+' <<<"${new##*:}")
  printf '  %-16s %-34s -> %s%s\n' "$folder" "${old##*:}" "${new##*:}" "$([ "$m1" = "$m2" ] || echo '   MAJOR: read the upgrade notes first')"
done

# Which hosts run each updated folder (hosts/<host> lists its folders)
folders=$(for c in "${changes[@]}"; do cut -d'|' -f2 <<<"$c"; done | sort -u)
hosts_for() { grep -lx "$1" hosts/prdsrv* 2>/dev/null | xargs -n1 basename; }
echo "Hosts:"
for h in $(for d in $folders; do hosts_for "$d"; done | sort -u); do
  echo "  $h: $(for d in $folders; do grep -qx "$d" "hosts/$h" && printf '%s ' "$d"; done)"
done
$dry && { echo "(dry run: nothing changed)"; exit 0; }
if ! $yes; then
  read -r -p "Update these now? Each app restarts for a few seconds; Caddy (every site) last. [y/N] " ok
  [ "$ok" = y ] || [ "$ok" = Y ] || { echo "Nothing changed."; exit 0; }
fi

# 2. Bump the tags, commit, push
summary=()
for c in "${changes[@]}"; do
  IFS='|' read -r f folder old new <<<"$c"
  sed -i '' "s|$old|$new|" "$f" 2>/dev/null || sed -i "s|$old|$new|" "$f"
  summary+=("$folder ${old##*:} to ${new##*:}")
done
msg="Update: $(printf '%s\n' "${summary[@]}" | sort -u | paste -sd ';' - | sed 's/;/; /g')"
git commit -qam "$msg" && git push -q && echo "Committed and pushed: $msg"

# 3. Each host: backup, pull, recreate the updated apps (Caddy last)
for h in $(for d in $folders; do hosts_for "$d"; done | sort -u); do
  apps=$(for d in $folders; do grep -qx "$d" "hosts/$h" && echo "$d"; done | grep -vx caddy || true)
  grep -qx caddy <<<"$folders" && grep -qx caddy "hosts/$h" && apps="$apps caddy"
  echo; echo "== $h: $apps"
  if $backup; then make -s -C "$LAB" backup NAME="$h" | tail -1; fi
  ssh "$h" "set -e; cd /opt/docker && git pull -q --ff-only
    for a in $apps; do
      cd /opt/docker/\$a
      if [ \$a = caddy ]; then docker compose build -q --pull && docker compose up -d --quiet-pull
      else docker compose pull -q && docker compose up -d --quiet-pull; fi
      echo \"  \$a: \$(docker compose ps --format '{{.Name}} {{.Status}}' | paste -sd ',' -)\"
    done"
done
echo; echo "Done. Check the apps work; to roll back: git revert HEAD, push, and re-run the host step."
