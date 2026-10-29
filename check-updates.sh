#!/usr/bin/env bash
# List newer releases of every pinned image (read-only: only asks the registries for tag lists).
#   ./check-updates.sh
# "update" = newer release in the same major version (usually safe: bump and redeploy).
# "major"  = a new major version exists (read the upgrade notes first; databases need care).
set -uo pipefail
cd "$(dirname "$0")"

tags() {  # <registry> <repository>: every tag, following pagination
  local reg=$1 repo=$2 tok="" url last="" page
  case $reg in
    docker.io)
      url="https://hub.docker.com/v2/repositories/${repo}/tags?page_size=100"
      while [ -n "$url" ] && [ "$url" != null ]; do
        page=$(curl -fs "$url") || return
        jq -r '.results[].name' <<<"$page"
        url=$(jq -r '.next' <<<"$page")
      done
      return ;;
    ghcr.io) tok=$(curl -fs "https://ghcr.io/token?scope=repository:${repo}:pull" | jq -r .token) ;;
    container-registry.oracle.com)
      tok=$(curl -fs "https://container-registry.oracle.com/auth?service=Oracle%20Registry&scope=repository:${repo}:pull" | jq -r '.token // empty') ;;
  esac
  while :; do
    page=$(curl -fs ${tok:+-H "Authorization: Bearer $tok"} "https://${reg}/v2/${repo}/tags/list?n=1000${last:+&last=$last}" | jq -r '.tags[]?') || return
    [ -z "$page" ] && return
    echo "$page"
    [ "$(wc -l <<<"$page")" -lt 1000 ] && return
    last=$(tail -1 <<<"$page")
  done
}

versions() {  # <image:tag>: every tag of the same shape (v prefix, number of parts, suffix), oldest first
  local name=${1%:*} tag=${1##*:} reg repo pattern
  case $name in
    */*.*/*|*.*/*) reg=${name%%/*}; repo=${name#*/} ;;
    */*) reg=docker.io; repo=$name ;;
    *) reg=docker.io; repo=library/$name ;;
  esac
  [ "$reg" = docker.io ] && repo=${repo#docker.io/}
  [ "$reg" = lscr.io ] && reg=ghcr.io  # LinuxServer's registry name serves the images on GHCR
  pattern="^$(sed -E 's/[0-9]+/[0-9]+/g; s/\./\\./g' <<<"$tag")\$"
  tags "$reg" "$repo" | grep -E "$pattern" | sort -V
}

newer_same_major() {  # <image:tag>: the newest tag in the same major version, if newer; else nothing
  local tag=${1##*:} all cur_major same
  all=$(versions "$1" || true)
  [ -n "$all" ] || return 0
  cur_major=$(grep -oE '^[^0-9]*[0-9]+' <<<"$tag")
  same=$(grep -E "^${cur_major}([^0-9]|$)" <<<"$all" | tail -1)
  [ -n "$same" ] && [ "$same" != "$tag" ] && [ "$(printf '%s\n%s\n' "$tag" "$same" | sort -V | tail -1)" = "$same" ] && echo "$same"
}

check() {  # <where> <image:tag>
  local where=$1 ref=$2 name=${2%:*} tag=${2##*:} all same major
  all=$(versions "$ref")
  if [ -z "$all" ]; then printf '%-28s %-34s %s\n' "${name##*/}" "$tag" "(could not read tags)"; return; fi
  local cur_major; cur_major=$(grep -oE '^[^0-9]*[0-9]+' <<<"$tag")
  same=$(grep -E "^${cur_major}([^0-9]|$)" <<<"$all" | tail -1)
  major=$(tail -1 <<<"$all")
  local note=""
  [ "$same" != "$tag" ] && [ "$(printf '%s\n%s\n' "$tag" "$same" | sort -V | tail -1)" = "$same" ] && note="update: $same"
  [ "$major" != "$same" ] && note="${note:+$note, }major: $major"
  printf '%-28s %-34s %s\n' "${name##*/}" "$tag" "${note:-up to date}"
}

# Sourced by update.sh for the functions above; run directly, it prints the table.
[ "${BASH_SOURCE[0]}" = "$0" ] || return 0

printf '%-28s %-34s %s\n' "image" "pinned" "newer"
for f in */docker-compose.yml; do
  grep -E '^\s*image:' "$f" | awk '{print $2}' | tr -d '"' | while read -r ref; do check "$f" "$ref"; done
done
grep -E '^FROM ' caddy/Dockerfile | awk '{print $2}' | while read -r ref; do check caddy/Dockerfile "$ref"; done
