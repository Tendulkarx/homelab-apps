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

check() {  # <where> <image:tag>
  local where=$1 ref=$2 name=${2%:*} tag=${2##*:} reg repo pattern all same major
  case $name in
    */*.*/*|*.*/*) reg=${name%%/*}; repo=${name#*/} ;;
    */*) reg=docker.io; repo=$name ;;
    *) reg=docker.io; repo=library/$name ;;
  esac
  [ "$reg" = docker.io ] && repo=${repo#docker.io/}
  # Compare like with like: same shape of tag (v prefix, number of parts, suffix)
  pattern="^$(sed -E 's/[0-9]+/[0-9]+/g; s/\./\\./g' <<<"$tag")\$"
  all=$(tags "$reg" "$repo" | grep -E "$pattern" | sort -V)
  if [ -z "$all" ]; then printf '%-28s %-34s %s\n' "${name##*/}" "$tag" "(could not read tags)"; return; fi
  local cur_major; cur_major=$(grep -oE '^[^0-9]*[0-9]+' <<<"$tag")
  same=$(grep -E "^${cur_major}([^0-9]|$)" <<<"$all" | tail -1)
  major=$(tail -1 <<<"$all")
  local note=""
  [ "$same" != "$tag" ] && [ "$(printf '%s\n%s\n' "$tag" "$same" | sort -V | tail -1)" = "$same" ] && note="update: $same"
  [ "$major" != "$same" ] && note="${note:+$note, }major: $major"
  printf '%-28s %-34s %s\n' "${name##*/}" "$tag" "${note:-up to date}"
}

printf '%-28s %-34s %s\n' "image" "pinned" "newer"
for f in */docker-compose.yml; do
  grep -E '^\s*image:' "$f" | awk '{print $2}' | tr -d '"' | while read -r ref; do check "$f" "$ref"; done
done
grep -E '^FROM ' caddy/Dockerfile | awk '{print $2}' | while read -r ref; do check caddy/Dockerfile "$ref"; done
