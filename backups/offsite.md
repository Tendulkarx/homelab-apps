# Off-site copy: own Google client

rclone signs in to Google Drive through a Google "OAuth client". Its shared one is being
retired during 2026 (rclone warns on every run), so the off-site copy needs its own. About
10 minutes in the browser, once.

## 1. Make the client (console.cloud.google.com)

1. New project `homelab-backups`.
2. APIs & Services > Library: enable **Google Drive API**.
3. Google Auth Platform (OAuth consent screen): app name `homelab-backups`, audience
   **External**, your address as support and developer contact. Under Data access, add the
   scope `.../auth/drive.file` (only files rclone makes; no Google review needed for it).
4. Audience: **Publish app** (In production). In "Testing" Google expires the sign-in after
   7 days and the nightly copy stops.
5. Clients > Create client: type **Desktop app**, name `rclone prdsrv2`. Copy the client ID
   and secret.

## 2. Keep them and sign in again (Mac)

Add two fields to 1Password item `prdsrv2-rclone` (vault Development): `client_id` and
`client_secret` (concealed). Then:

```bash
bash ~/development/homelab-apps/backups/setup-offsite.sh --reauth
```

Google shows "Google hasn't verified this app": it is your own app, so choose Advanced >
Go to homelab-backups. The script saves the new sign-in, rewrites the server's config and makes
a test copy. The encryption keys do not change.

## 3. Remove the old copies

With `drive.file`, each client sees only the files it made, so rclone can no longer see (or
prune) what the shared client made. drive.google.com now shows two `homelab-offsite` folders:
delete the older one.
