#!/usr/bin/env python3
"""Build the Homelab board in Homarr through its API. Run on prdsrv1: python3 build-board.py [--items]

Only needed to rebuild Homarr from nothing (a restored db.sqlite plus SECRET_ENCRYPTION_KEY already
has everything). First make ~/.homarr-setup (mode 700) holding, each written server to server so
nothing is shown (the Homarr API key comes from 1Password, `homelab-homarr-api`):
  prx1-token.json   `pveum user token add homarr@pve dash --privsep 0 --output-format json` on prx1
  prx2-token.json   the same on prx2 (user homarr@pve with role PVEAuditor on /)
  pihole-password   PIHOLE_WEBPASSWORD from prdsrv2's pihole/.env
  paperless-token   `manage.py drf_create_token turbx` in paperless-webserver
Uptime Kuma needs its status page `homelab`. Run once without --items (apps, integrations, board),
then with --items (widgets). Prints names and results only. Delete ~/.homarr-setup afterwards.
Built 2026-09-30; the layout was then arranged by hand in Homarr's edit mode.
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

BASE = "https://dash.example.com"
SETUP = os.path.expanduser("~/.homarr-setup")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme"))
from homarr_session import api_key  # noqa: E402  (1Password, homelab-homarr-api)

KEY = api_key()
CTX = ssl.create_default_context()
ICON = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/{}.svg"


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, headers={"ApiKey": KEY, "Content-Type": "application/json"})
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, context=CTX, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")[:300]
        raise SystemExit(f"{method} {path}: HTTP {e.code} {msg}")


def trpc_query(proc):
    res = call("GET", f"/api/trpc/{proc}")
    return res["result"]["data"]["json"]


def trpc_mutation(proc, payload):
    res = call("POST", f"/api/trpc/{proc}", {"json": payload})
    return (res or {}).get("result", {}).get("data", {}).get("json")


def read(name):
    return open(f"{SETUP}/{name}").read().strip()


# ---- Apps ------------------------------------------------------------------------------------
APPS = [
    # name, description, icon slug, href, ping url
    ("Paperless", "Documents and OCR", "paperless-ngx", "https://paperless.example.com", "https://paperless.example.com"),
    ("n8n", "Automation; runs property-search", "n8n", "https://n8n.example.com", "https://n8n.example.com"),
    ("Metabase", "Reporting and dashboards", "metabase", "https://metabase.example.com", "https://metabase.example.com/api/health"),
    ("House Hunting", "property-search dashboard", "metabase", "https://metabase.example.com/dashboard/3", ""),
    ("Uptime Kuma", "Monitors and alerts", "uptime-kuma", "https://uptime.example.com", "https://uptime.example.com"),
    ("Status page", "Every monitor on one page", "uptime-kuma", "https://uptime.example.com/status/homelab", ""),
    ("Logs", "Dozzle: container logs, all hosts", "dozzle", "https://logs.example.com", "https://logs.example.com"),
    ("Arcane", "Docker stacks on prdsrv1", "arcane", "https://arcane.example.com", "https://arcane.example.com"),
    ("Pi-hole", "DNS and ad blocking (primary)", "pi-hole", "https://pihole.example.com/admin", "https://pihole.example.com/admin"),
    ("prx1", "Proxmox VE: prdsrv1, prdsrv2, tstsrv1", "proxmox", "https://prx1.example.com", "https://prx1.example.com"),
    ("prx2", "Proxmox VE: prdsrv3", "proxmox", "https://prx2.example.com", "https://prx2.example.com"),
    ("Backup Server", "Proxmox Backup Server on prx2", "proxmox", "https://10.69.20.131:8007", ""),
    ("UniFi", "Network dashboard on the UDM SE", "ubiquiti-unifi", "https://10.69.1.1/network/default/dashboard", ""),
    ("Cloudflare", "example.com DNS", "cloudflare", "https://dash.cloudflare.com", ""),
]

existing = {a["name"]: a["id"] for a in call("GET", "/api/apps")}
for name, desc, icon, href, ping in APPS:
    if name not in existing:
        call("POST", "/api/apps", {"name": name, "description": desc, "iconUrl": ICON.format(icon), "href": href, "pingUrl": ping or None})
apps = {a["name"]: a["id"] for a in call("GET", "/api/apps")}
print(f"apps: {len(apps)}")

# ---- Integrations (tested by Homarr before saving) --------------------------------------------
current = {i["name"]: i["id"] for i in trpc_query("integration.all")}
INTEGRATIONS = []
for host, url in (("prx1", "https://prx1.example.com"), ("prx2", "https://prx2.example.com")):
    tok = json.load(open(f"{SETUP}/{host}-token.json"))
    INTEGRATIONS.append((f"Proxmox {host}", "proxmox", url, [
        {"kind": "username", "value": "homarr"}, {"kind": "realm", "value": "pve"},
        {"kind": "tokenId", "value": "dash"}, {"kind": "apiKey", "value": tok["value"]}], host))
INTEGRATIONS += [
    ("Pi-hole", "piHole", "http://10.69.20.114:8081", [{"kind": "apiKey", "value": read("pihole-password")}], "Pi-hole"),
    ("Uptime Kuma", "uptimeKuma", "https://uptime.example.com", [{"kind": "slug", "value": "homelab"}], "Uptime Kuma"),
    ("Paperless", "paperlessNgx", "http://paperless-webserver:8000", [{"kind": "apiKey", "value": read("paperless-token")}], "Paperless"),
]
for name, kind, url, secrets, app in INTEGRATIONS:
    if name in current:
        print(f"integration {name}: exists")
        continue
    res = trpc_mutation("integration.create", {"name": name, "kind": kind, "url": url, "secrets": secrets,
                                               "attemptSearchEngineCreation": False, "app": {"id": apps[app]}})
    print(f"integration {name}: {'FAILED ' + json.dumps(res.get('error'))[:200] if isinstance(res, dict) and res.get('error') else 'created'}")
ints = {i["name"]: i["id"] for i in trpc_query("integration.all")}

# ---- Board -----------------------------------------------------------------------------------
boards = {b["name"]: b["id"] for b in call("GET", "/api/boards")}
if "Homelab" not in boards:
    call("POST", "/api/boards", {"name": "Homelab", "columnCount": 12, "isPublic": False})
    boards = {b["name"]: b["id"] for b in call("GET", "/api/boards")}
bid = boards["Homelab"]
if "--items" not in sys.argv:
    print("board Homelab ready; run again with --items to add the widgets")
    sys.exit(0)

HOUNSLOW = {"name": "Hounslow", "latitude": 51.4668, "longitude": -0.3615}


def item(kind, options=None, integrations=()):
    missing = [n for n in integrations if n not in ints]
    if missing:
        print(f"widget {kind}: skipped, missing integration {missing}")
        return
    call("POST", "/api/boards/items", {"boardId": bid, "kind": kind, "options": options or {},
                                       "integrationIds": [ints[n] for n in integrations]})
    print(f"widget {kind}{' ' + options.get('_label', '') if options and '_label' in options else ''}: added")


item("clock", {"showDate": True, "useCustomTimezone": True, "timezone": "Europe/London", "showWeather": True,
               "weatherLocation": HOUNSLOW})
item("weather", {"location": HOUNSLOW, "hasForecast": True, "forecastDayCount": 5, "showCity": True})
item("uptimeKuma", {"showAverageUptime": True, "showUptimeRing": True, "showTotalMonitors": True,
                    "showUpCount": True, "showDownCount": True, "showPausedCount": True}, ["Uptime Kuma"])
item("healthMonitoring", {"cpu": True, "memory": True, "fileSystem": True, "showUptime": True,
                          "defaultTab": "cluster"}, ["Proxmox prx1", "Proxmox prx2"])
item("dnsHoleSummary", {"usePiHoleColors": True, "layout": "grid"}, ["Pi-hole"])
item("dnsHoleControls", {"showToggleAllButtons": True}, ["Pi-hole"])
for name, *_ in APPS:
    item("app", {"appId": apps[name], "openInNewTab": True, "showTitle": True, "pingEnabled": True,
                 "descriptionDisplayMode": "tooltip", "layout": "column", "_label": name})
item("dockerContainers", {"enableRowSorting": True})
item("paperlessNgx", {"showDocumentsTotal": True, "showDocumentsInbox": True, "showInboxRing": True,
                      "showCorrespondents": True, "showTags": True}, ["Paperless"])
item("notebook", {"showToolbar": True, "allowReadOnlyCheck": True, "content": (
    "<h3>Homelab</h3>"
    "<p><b>prdsrv1</b> .113 apps and Caddy · <b>prdsrv2</b> .114 databases, Pi-hole · "
    "<b>prdsrv3</b> .115 Uptime Kuma, Pi-hole 2 · <b>tstsrv1</b> .200 lab</p>"
    "<p>Backups: dumps 01:30, off-site 03:00, Backup Server 03:30. Alerts: Gmail label Homelab.</p>"
    "<p>Repos: proxmox-lab (hosts, VMs), homelab-apps (/opt/docker). "
    "Status page: uptime.example.com/status/homelab</p>")})
call("PATCH", f"/api/boards/{bid}/home")
print("board Homelab: widgets added, set as home board")
