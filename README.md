# homelab-apps

The Docker apps on **prdsrv2** (10.69.20.114): one folder per app, each with its
`docker-compose.yml`. On the server this repo *is* `/opt/docker`, so what is committed here is
what runs. The VM itself (and the Proxmox hosts) are built by
[proxmox-lab](https://github.com/Tendulkarx/proxmox-lab).

| Folder | What it is | Address |
|---|---|---|
| `caddy` | Reverse proxy and HTTPS for everything below (custom build with the Cloudflare DNS module) | ports 80, 443 |
| `pihole` | DNS for the lab | 10.69.20.114:53, `pihole.` |
| `homepage` | Dashboard | `home.` |
| `paperless` | Paperless-ngx with Redis, Tika and Gotenberg | `paperless.` |
| `n8n` | Automation | `n8n.` |
| `metabase` | Reporting | `metabase.` |
| `uptime-kuma` | Uptime monitoring | `uptime.` |
| `arcane` | Docker web UI (edits the files in this repo on the server) | `arcane.` |
| `postgres` | PostgreSQL 18 (Paperless, Metabase and own databases) | 10.69.20.114:5432 |
| `sqlserver` | SQL Server 2022 | 10.69.20.114:1433 |
| `oracle` | Oracle Database Free | 10.69.20.114:1521 |

Web addresses are `<name>.<CADDY_BASE_DOMAIN>`; Caddy also proxies the Proxmox hosts as `prx1.`
and `prx2.`. Every app shares the external Docker network `proxy`, so apps reach each other by
container name (for example `postgres:5432`).

## Making a change

Edit on the Mac (`~/development/homelab-apps`) or on the server (directly or in Arcane), then
bring the other copy up to date. Pull before editing, wherever you edit.

```bash
# Mac
git pull
# ...edit...
git commit -am "paperless: what changed and why" && git push

# Server
ssh turbx@10.69.20.114
cd /opt/docker && git pull
cd paperless && docker compose up -d        # recreates only what changed
```

Edited on the server or in Arcane instead: commit and push from `/opt/docker` (it has its own
deploy key for this repo), then `git pull` on the Mac.

## Updating an app

Images are pinned to exact versions, so nothing changes by surprise and rolling back is one
line. To see what is out of date, run on the Mac:

```bash
./check-updates.sh      # "update: x" = newer in the same major; "major: y" = read the notes first
```

SQL Server 2025 upgrades database files on first start and cannot be rolled back by changing
the tag: copy `sqlserver/data` aside (container stopped) before any major SQL Server update.

Take a backup first (`make backup-vm HOST=10.69.20.130 VMID=101` in proxmox-lab), check the
app's release notes, then:

```bash
# change the tag in <app>/docker-compose.yml (Caddy: both FROM lines in caddy/Dockerfile)
git commit -am "n8n: 2.40.5 to 2.41.0" && git push
# on the server
cd /opt/docker && git pull && cd n8n && docker compose pull && docker compose up -d
# Caddy is built locally: docker compose build --pull && docker compose up -d
```

To roll back, put the old tag back and run the same commands. Take care with major versions of
Postgres, Oracle, Paperless and n8n: they change stored data, so read the upgrade notes and make
sure a fresh backup exists first.

## Secrets

`.env` files are never committed. Their values are in 1Password (vault **Development**), one
item per app named `prdsrv2-<app>`, one field per line of the file. Each `.env.example` lists
every setting with its 1Password reference, so a lost `.env` is rebuilt with:

```bash
op inject -i .env.example -o .env
```

`postgres/init/02-users.sql` is not committed either (it contains passwords); its original
values are in `prdsrv2-postgres`.

## What is not in git, and where it is kept

App data (`*/data/`, Paperless `media`, `consume` and `export`), Caddy's certificates and
runtime config, and logs are ignored. They are covered by the nightly Proxmox backup of prdsrv2
(02:30, last two kept, copied to the second host at 06:00); see `docs/disaster-recovery.md` in
proxmox-lab.
