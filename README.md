# homelab-apps

The Docker apps of the homelab, one folder per app, each with its `docker-compose.yml`. The same
repo is cloned at `/opt/docker` on three hosts, and each host runs only its own folders (table
below), so what is committed here is what runs. The hosts themselves are built by
[proxmox-lab](https://github.com/Tendulkarx/proxmox-lab).

- **prdsrv1** (10.69.20.113): the apps and Caddy.
- **prdsrv2** (10.69.20.114): the databases, primary Pi-hole, property-search (beside Postgres).
- **prdsrv3** (10.69.20.115, container on prx2): what must outlive prdsrv2.

Each host checks out only its own folders (listed in `hosts/<host>`, see `hosts/README.md`).

| Folder | Runs on | What it is | Address |
|---|---|---|---|
| `caddy` | prdsrv1 | Reverse proxy and HTTPS for everything below (custom build with the Cloudflare DNS module) | ports 80, 443 |
| `paperless` | prdsrv1 | Paperless-ngx with Redis, Tika and Gotenberg | `paperless.` |
| `n8n` | prdsrv1 | Automation; starts property-search on prdsrv2 over SSH | `n8n.` |
| `metabase` | prdsrv1 | Reporting | `metabase.` |
| `dozzle` | prdsrv1 | Live logs of every container on all three hosts (login `turbx`) | `logs.` |
| `homarr` | prdsrv1 | Dashboard: every app, host, VM, container, DNS and monitor on one page (replaced Homepage 2026-09-30) | `home.`, `dash.` |
| `docker-socket-proxy` | all three | Read-only Docker API for Homarr and the Beszel agents (lists containers, refuses everything else) | port 2375, prdsrv1 only |
| `beszel-agent` | all three | Sends the host's CPU, memory, disk, network and container stats to the Beszel hub; connects out, listens on no port | none |
| `arcane` | prdsrv1 | Docker web UI for prdsrv1's stacks (edits the files in this repo on the server); sees only this host's folders and containers | `arcane.` |
| `postgres` | prdsrv2 | PostgreSQL 18 (Paperless, Metabase and own databases) | 10.69.20.114:5432 |
| `sqlserver` | prdsrv2 | SQL Server 2022 | 10.69.20.114:1433 |
| `oracle` | prdsrv2 | Oracle Database Free | 10.69.20.114:1521 |
| `pihole` | prdsrv2, prdsrv3 | DNS for the lab (primary; second on prdsrv3) | .114 and .115 port 53; admin pages `pihole.` and `pihole2.` |
| `property-search` | prdsrv2 | Rightmove scraper job, run by n8n via `run.sh` (not a service); a log file per run in `logs/` | none |
| `dozzle-agent` | prdsrv2, prdsrv3 | Lets Dozzle read this host's logs (the lab's own certificate) | port 7007 |
| `uptime-kuma` | prdsrv3 | Uptime monitoring | `uptime.` |
| `beszel` | prdsrv3 | Beszel hub: resource history and alerts for the VMs, prdsrv3 and both Proxmox hosts | `beszel.` |
| `nebula-sync` | prdsrv3 | Copies lists and local DNS from the primary Pi-hole every hour | none |
| `backups` | prdsrv1, prdsrv2 | Nightly dumps of what runs on the host into `/opt/backups` (01:30, 14 days), encrypted off-site copy (03:00); timers from proxmox-lab | none |

Apps on prdsrv1 still reach Postgres as `postgres`: their compose files map that name to
10.69.20.114 (`extra_hosts`).

Web addresses are `<name>.<CADDY_BASE_DOMAIN>`; Caddy also proxies the Proxmox hosts as `prx1.`
and `prx2.`. Every app shares the external Docker network `proxy`, so apps reach each other by
container name (for example `postgres:5432`).

## Per-host settings

A host's own values live in each folder's `.env` (not in git): `PIHOLE_BIND_IP` and
`PIHOLE_WEB_BIND` (Pi-hole), `UPTIME_KUMA_BIND`, `DOZZLE_HOSTNAME`/`AGENT_BIND` (agents),
`DOZZLE_REMOTE_AGENT` (Dozzle), `SYSTEM_NAME` and `DOCKER_HOST` (Beszel agent), `HUB_BIND`
(Beszel hub). See proxmox-lab `docs/lab-rebuild-plan.md`, phases 3 and 6.

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

When an app moves off prdsrv1, delete its project in Arcane afterwards (Destroy, with "remove
files" and "remove volumes" both off): Arcane keeps a record of every folder it has seen, and a
folder that has gone shows as a stopped project.

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

After pulling a change to `caddy/etc/Caddyfile`, reload it without downtime:
`docker exec caddy caddy reload --config /etc/caddy/Caddyfile`. (Caddy mounts the `etc`
folder; a mount of the file alone kept the old copy after `git pull` until a restart.)

To roll back, put the old tag back and run the same commands. Take care with major versions of
Postgres, Oracle, Paperless and n8n: they change stored data, so read the upgrade notes and make
sure a fresh backup exists first.

## Secrets

`.env` files are never committed. Their values are in 1Password (vault **Development**), one
item per app named `homelab-<app>` (host-agnostic, so moving an app to another host needs no rename), one
field per line of the file. Per-host values (see above) are added by hand. Each `.env.example` lists
every setting with its 1Password reference, so a lost `.env` is rebuilt with:

```bash
op inject -i .env.example -o .env
```

Dozzle's login (user `turbx`) is the 1Password item `homelab-dozzle`. The server only holds a
hash of it in `dozzle/data/users.yml`, which is not committed; to rebuild that file, from the Mac:

```bash
op read op://Development/homelab-dozzle/password | ssh prdsrv1 'cd /opt/docker/dozzle && mkdir -p data &&
  docker run --rm amir20/dozzle:v11.1.2 generate turbx --password "$(cat)" > data/users.yml'
```

Beszel agents register once, then the hub knows each by the fingerprint in its `data/`
folder (the Proxmox hosts: `/var/lib/beszel-agent`). The hub's universal token is kept off, so
a rebuilt machine, or a new one, is refused until it registers again: in the hub, Settings >
Tokens & Fingerprints, switch the universal token on for an hour, start the agent, switch it
off. A hub rebuilt from nothing (no `beszel/data`) also has a new key: copy its public key and
token into `Homelab - Beszel` (section `agents`), rebuild each agent's `.env`, run `make hosts
ARGS="--tags beszel"` in proxmox-lab for prx1 and prx2, and update the system ids in
`homarr/theme/layout.py`.

`postgres/init/02-users.sql` is not committed either (it contains passwords); its original
values are in `homelab-postgres`.

## What is not in git, and where it is kept

App data (`*/data/`, Paperless `media`, `consume` and `export`), Caddy's certificates and
runtime config, and logs are ignored. They are covered by the nightly Proxmox backups of each
host (to the Backup Server on prx2, and to `data` with a copy on prx2), and the databases, n8n
and Paperless also by `backups/` (nightly dumps plus an encrypted off-site copy); see
`docs/disaster-recovery.md` in proxmox-lab.
