#!/usr/bin/env python3
"""Lay out the Homelab board. Run on prdsrv1 next to homarr_session.py (see README.md).

One plain section holds everything. Headed groups are Homarr "dynamic" sections: titled frames
that never collapse. Every service is an app tile in the same compact style (name left, icon
right, description on hover). The look is set separately by apply_theme.py.
"""
import random
import string

from homarr_session import login, mutate, query

login()
b = query("board.getBoardByName", {"name": "Homelab"})
L = b["layouts"][0]["id"]
top = next(s for s in b["sections"] if s["kind"] == "empty" and s["yOffset"] == 0)["id"]
ints = {i["name"]: i["id"] for i in query("integration.all")}


def nid():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=24))


ICON = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/{}.svg"
# Tiles added after build-board.py: (name, description, icon, href, ping url)
EXTRA_APPS = [
    ("Pi-hole 2", "DNS and ad blocking (second, prdsrv3)", "pi-hole",
     "https://pihole2.example.com/admin", "https://pihole2.example.com/admin"),
    ("Off-site backups", "Encrypted nightly copies in Google Drive (03:00)", "google-drive",
     "https://drive.google.com/drive/search?q=homelab-offsite", None),
]
apps = {a["name"]: a["id"] for a in query("app.all")}
for name, desc, icon, href, ping in EXTRA_APPS:
    if name not in apps:
        mutate("app.create", {"name": name, "description": desc, "iconUrl": ICON.format(icon),
                              "href": href, "pingUrl": ping})
apps = {a["name"]: a["id"] for a in query("app.all")}
app_name = {v: k for k, v in apps.items()}

# Headed groups: (title, 20 characters at most; y; height), full width in the plain section.
# Links first (apps, monitoring and network, servers), then the live panels below them.
GROUPS = [("Apps", 2, 1), ("Monitoring & network", 3, 1), ("Servers & backups", 4, 1),
          ("Proxmox hosts", 5, 4), ("Containers & updates", 9, 6), ("Documents & notes", 15, 3)]
old_dyn = {s["options"]["title"]: s["id"] for s in b["sections"] if s["kind"] == "dynamic"}
dyn = {title: old_dyn.get(title) or nid() for title, *_ in GROUPS}
sections = [{"id": top, "kind": "empty", "xOffset": 0, "yOffset": 0}] + [
    {"id": dyn[t], "kind": "dynamic", "options": {"title": t, "customCssClasses": ["hl-group"], "borderColor": ""},
     "layouts": [{"layoutId": L, "parentSectionId": top, "xOffset": 0, "yOffset": y, "width": 12, "height": h}]}
    for t, y, h in GROUPS]

# Each link group is one balanced row: six narrow tiles, or four wide ones
TILES = {
    "Apps": ["Paperless", "n8n", "Metabase", "Logs", "Arcane", "GitHub"],
    "Monitoring & network": ["Uptime Kuma", "Status page", "Pi-hole", "Pi-hole 2", "UniFi", "Cloudflare"],
    "Servers & backups": ["prx1", "prx2", "Backup Server", "Off-site backups"],
}
ON_BOARD = {n for names in TILES.values() for n in names}

GH = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/{}.png"


def repo(name, provider, identifier, icon, prefix="", precision=3):
    return {"id": name.lower().replace(" ", "-"), "provider": provider, "identifier": identifier, "name": name,
            "iconUrl": GH.format(icon), "versionFilter": {"prefix": prefix, "precision": precision}}


# Latest release of everything homelab-apps pins, to compare with the compose files. Docker Hub
# wherever the project publishes there: anonymous GitHub allows 60 requests an hour, which two
# page loads of a dozen repositories used up.
RELEASES = {
    "newReleaseWithin": "1w", "staleReleaseWithin": "6M", "showOnlyHighlighted": False, "showDetails": True,
    "showOnlyIcon": False, "topReleases": 0,
    "repositories": [
        repo("Homarr", "github", "homarr-labs/homarr", "homarr", "v"),
        repo("Paperless", "github", "paperless-ngx/paperless-ngx", "paperless-ngx", "v"),
        repo("Arcane", "github", "getarcaneapp/arcane", "arcane", "v"),
        repo("nebula-sync", "github", "lovelaze/nebula-sync", "pi-hole", "v"),
        repo("Pi-hole", "dockerHub", "pihole/pihole", "pi-hole"),
        repo("Uptime Kuma", "dockerHub", "louislam/uptime-kuma", "uptime-kuma"),
        repo("n8n 2", "dockerHub", "n8nio/n8n", "n8n", "2.", 2),
        repo("Metabase", "dockerHub", "metabase/metabase", "metabase", "v0."),
        repo("Dozzle", "dockerHub", "amir20/dozzle", "dozzle", "v"),
        repo("Caddy", "dockerHub", "caddy", "caddy"),
        repo("Gotenberg", "dockerHub", "gotenberg/gotenberg", "gotenberg"),
        repo("Postgres 18", "dockerHub", "postgres", "postgres", "18.", 1),
        repo("Redis 8", "dockerHub", "redis", "redis", "8.", 2),
    ],
}

items = [i for i in b["items"] if i["kind"] != "dnsHoleControls"
         and not (i["kind"] == "app" and app_name.get(i["options"].get("appId")) not in ON_BOARD)]
have = {app_name.get(i["options"].get("appId")) for i in items if i["kind"] == "app"}
for name in (n for n in ON_BOARD if n not in have):
    items.append({"id": nid(), "kind": "app", "options": {"appId": apps[name]}, "integrationIds": [],
                  "advancedOptions": {"title": None, "customCssClasses": [], "borderColor": ""}, "layouts": []})
if not any(i["kind"] == "releases" for i in items):
    items.append({"id": nid(), "kind": "releases", "options": {}, "integrationIds": [],
                  "advancedOptions": {"title": None, "customCssClasses": [], "borderColor": ""}, "layouts": []})

def at(it, section, x, y, w, h):
    it["layouts"] = [{"layoutId": L, "sectionId": section, "xOffset": x, "yOffset": y, "width": w, "height": h}]


for it in items:
    it["layouts"] = []
    k = it["kind"]
    if k == "app":
        name = app_name[it["options"]["appId"]]
        it["options"].update(layout="row", showTitle=True, openInNewTab=True, pingEnabled=True,
                             descriptionDisplayMode="tooltip")
        for group, names in TILES.items():
            if name in names:
                w = 12 // len(names)
                at(it, dyn[group], names.index(name) * w, 0, w, 1)
    elif k == "clock":
        at(it, top, 0, 0, 3, 2)
    elif k == "weather":
        at(it, top, 3, 0, 3, 2)
    elif k == "uptimeKuma":
        at(it, top, 6, 0, 3, 2)
    elif k == "dnsHoleSummary":
        at(it, top, 9, 0, 3, 2)
    elif k == "healthMonitoring":
        # Standalone hosts: the Nodes list is always 1/1 and repeats the CPU and RAM above it
        # (prx1 runs no containers, so it lists VMs and storage only)
        prx2 = ints["Proxmox prx2"] in it["integrationIds"]
        it["options"]["visibleClusterSections"] = ["qemu", "lxc", "storage"] if prx2 else ["qemu", "storage"]
        at(it, dyn["Proxmox hosts"], 6 if prx2 else 0, 0, 6, 4)
    elif k == "dockerContainers":
        at(it, dyn["Containers & updates"], 0, 0, 8, 6)
    elif k == "releases":
        it["options"] = RELEASES
        at(it, dyn["Containers & updates"], 8, 0, 4, 6)
    elif k == "paperlessNgx":
        at(it, dyn["Documents & notes"], 0, 0, 6, 3)
    elif k == "notebook":
        at(it, dyn["Documents & notes"], 6, 0, 6, 3)
    if not it["layouts"]:
        raise SystemExit(f"no place for {k}")

mutate("board.saveBoard", {"id": b["id"], "sections": sections, "items": items})
print(f"layout saved: {len(GROUPS)} headed groups, {len(items)} items, no collapsible sections")

print("layout done; set the look with apply_theme.py")
