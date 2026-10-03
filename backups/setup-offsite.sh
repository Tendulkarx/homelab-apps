#!/usr/bin/env bash
# One-off, on the Mac: connect prdsrv2's off-site copy (offsite.sh) to Google Drive.
#
#     bash backups/setup-offsite.sh
#
# First run: a browser opens for Google sign-in. rclone asks only for the drive.file scope,
# so it can see the files it makes and nothing else in the Drive. Two random encryption keys are
# made. The Drive token and the keys go into 1Password item homelab-rclone-offsite (vault Development):
# without the keys the off-site copies cannot be read, so that item is the only way back.
# Later runs (a rebuilt prdsrv2) read the item and only rewrite the server's rclone config.
#
# Own Google client (rclone's shared one is being retired in 2026): make a Desktop OAuth client
# in Google Cloud (offsite.md in this folder), add fields client_id and client_secret to
# the 1Password item, then run this again with --reauth to sign in through it.
set -euo pipefail

VAULT=Development
ITEM=homelab-rclone-offsite
# Every host with db_backups (proxmox-lab inventory): prdsrv2 (databases), prdsrv1 (n8n, Paperless)
HOSTS=(turbx@10.69.20.114 turbx@10.69.20.113)
ssh_to() { ssh -i "$HOME/.ssh/id_ed25519_homelab" -o BatchMode=yes "$@"; }

command -v rclone >/dev/null || brew install rclone

valid_token() { printf '%s' "$1" | python3 -c 'import json,sys; assert "refresh_token" in json.load(sys.stdin)' 2>/dev/null; }
field() { op read "op://$VAULT/$ITEM/$1" 2>/dev/null || true; }

authorize() {
  # To stderr: stdout is the token, captured by the caller.
  echo "A browser opens: sign in with the Google account for the backups and allow rclone." >&2
  # rclone takes and returns its settings as unpadded base64 JSON; the reply holds the token.
  opts=$(CID="${1:-}" CSECRET="${2:-}" python3 -c '
import base64, json, os
o = {"scope": "drive.file"}
if os.environ["CID"]:
    o.update(client_id=os.environ["CID"], client_secret=os.environ["CSECRET"])
print(base64.b64encode(json.dumps(o).encode()).decode().rstrip("="))')
  rclone authorize drive "$opts" | sed -n '/--->$/{n;p;}' | python3 -c '
import base64, json, sys
blob = sys.stdin.read().strip()
print(json.loads(base64.b64decode(blob + "=" * (-len(blob) % 4)))["token"])'
}

if ! op item get "$ITEM" --vault "$VAULT" >/dev/null 2>&1; then
  token=$(authorize)
  valid_token "$token" || { echo "No valid token from rclone authorize; nothing saved"; exit 1; }
  op item create --vault "$VAULT" --category password --title "$ITEM" \
    --tags homelab \
    "drive_token[concealed]=$token" \
    "crypt_password[concealed]=$(openssl rand -base64 32)" \
    "crypt_salt[concealed]=$(openssl rand -base64 32)" \
    "notesPlain=rclone for prdsrv2's off-site copy (homelab-apps backups/offsite.sh). The crypt keys are the only way to read the copies in Google Drive folder homelab-offsite." \
    >/dev/null
  echo "Saved to 1Password: $VAULT/$ITEM"
elif [ "${1:-}" = "--reauth" ]; then
  token=$(authorize "$(field client_id)" "$(field client_secret)")
  valid_token "$token" || { echo "No valid token from rclone authorize; nothing saved"; exit 1; }
  op item edit "$ITEM" --vault "$VAULT" "drive_token[concealed]=$token" >/dev/null
  echo "New Drive token saved to 1Password: $VAULT/$ITEM"
fi

token=$(op read "op://$VAULT/$ITEM/drive_token")
pass=$(rclone obscure "$(op read "op://$VAULT/$ITEM/crypt_password")")
salt=$(rclone obscure "$(op read "op://$VAULT/$ITEM/crypt_salt")")

cid=$(field client_id)
csecret=$(field client_secret)
conf() {
  printf '[gdrive]\ntype = drive\nscope = drive.file\ntoken = %s\n' "$token"
  [ -z "$cid" ] || printf 'client_id = %s\nclient_secret = %s\n' "$cid" "$csecret"
  printf '\n[offsite]\ntype = crypt\nremote = gdrive:homelab-offsite\npassword = %s\npassword2 = %s\n' "$pass" "$salt"
}
for host in "${HOSTS[@]}"; do
  conf | ssh_to "$host" 'sudo install -d -m 700 /root/.config/rclone &&
    sudo sh -c "umask 077; cat > /root/.config/rclone/rclone.conf"'
  echo "rclone config written on $host"
done
unset token pass salt cid csecret
echo "Test copy from prdsrv2:"
ssh_to "${HOSTS[0]}" 'sudo rclone mkdir offsite:daily && sudo /opt/docker/backups/offsite.sh'
