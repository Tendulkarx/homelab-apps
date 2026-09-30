#!/usr/bin/env bash
# One-off, on the Mac: connect prdsrv2's off-site copy (offsite.sh) to Google Drive.
#
#     bash backups/setup-offsite.sh
#
# First run: a browser opens for Google sign-in. rclone asks only for the drive.file scope,
# so it can see the files it makes and nothing else in the Drive. Two random encryption keys are
# made. The Drive token and the keys go into 1Password item prdsrv2-rclone (vault Development):
# without the keys the off-site copies cannot be read, so that item is the only way back.
# Later runs (a rebuilt prdsrv2) read the item and only rewrite the server's rclone config.
set -euo pipefail

VAULT=Development
ITEM=prdsrv2-rclone
HOST=turbx@10.69.20.114
SSH=(ssh -i "$HOME/.ssh/id_ed25519_homelab" -o BatchMode=yes "$HOST")

command -v rclone >/dev/null || brew install rclone

if ! op item get "$ITEM" --vault "$VAULT" >/dev/null 2>&1; then
  echo "A browser opens: sign in with the Google account for the backups and allow rclone."
  # rclone takes and returns its settings as unpadded base64 JSON; the reply holds the token.
  opts=$(python3 -c 'import base64,json; print(base64.b64encode(json.dumps({"scope": "drive.file"}).encode()).decode().rstrip("="))')
  token=$(rclone authorize drive "$opts" | sed -n '/--->$/{n;p;}' | python3 -c '
import base64, json, sys
blob = sys.stdin.read().strip()
print(json.loads(base64.b64decode(blob + "=" * (-len(blob) % 4)))["token"])')
  [ -n "$token" ] || { echo "No token from rclone authorize"; exit 1; }
  op item create --vault "$VAULT" --category password --title "$ITEM" \
    --tags homelab \
    "drive_token[concealed]=$token" \
    "crypt_password[concealed]=$(openssl rand -base64 32)" \
    "crypt_salt[concealed]=$(openssl rand -base64 32)" \
    "notesPlain=rclone for prdsrv2's off-site copy (homelab-apps backups/offsite.sh). The crypt keys are the only way to read the copies in Google Drive folder homelab-offsite." \
    >/dev/null
  echo "Saved to 1Password: $VAULT/$ITEM"
fi

token=$(op read "op://$VAULT/$ITEM/drive_token")
pass=$(rclone obscure "$(op read "op://$VAULT/$ITEM/crypt_password")")
salt=$(rclone obscure "$(op read "op://$VAULT/$ITEM/crypt_salt")")

printf '[gdrive]\ntype = drive\nscope = drive.file\ntoken = %s\n\n[offsite]\ntype = crypt\nremote = gdrive:homelab-offsite\npassword = %s\npassword2 = %s\n' \
  "$token" "$pass" "$salt" |
  "${SSH[@]}" 'sudo install -d -m 700 /root/.config/rclone &&
    sudo sh -c "umask 077; cat > /root/.config/rclone/rclone.conf"'
unset token pass salt
echo "rclone config written on prdsrv2. Test copy:"
"${SSH[@]}" 'sudo rclone mkdir offsite:daily && sudo /opt/docker/backups/offsite.sh'
