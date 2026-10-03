#!/usr/bin/env python3
"""Lay out the Homelab board (Homarr 2). Run on the Mac from this folder; Touch ID once.

  python3 layout.py            save the layout
  python3 layout.py --dry-run  show what would change, save nothing

Widget settings are defaults for new widgets only: what you change in Homarr itself (a chart's
period, which figures a card shows) stays. One plain section holds everything; headed groups are Homarr containers that never collapse.
The app tiles come from ../apps.toml (one balanced row per group): edit that file, then run this.
Homarr 2 keeps two layouts per board, Base (desktop, 12 columns) and Mobile (3 columns); this
sets the Base positions and keeps Mobile's own, adding new things at the bottom of Mobile.
The look is set separately by apply_theme.py.
"""
import random
import string
import sys
import tomllib
from pathlib import Path

from homarr_session import login, mutate, query

DRY = "--dry-run" in sys.argv
ICON = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/{}.svg"
GH = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/{}.png"

# Headed groups: (title, 20 characters at most; y; height) in Base, full width.
# Links first (apps, monitoring and network, servers), then the live panels below them.
GROUPS = [("Apps", 2, 1), ("Monitoring & network", 3, 1), ("Infrastructure", 4, 1),
          ("Servers", 5, 3), ("Host history", 8, 4), ("Containers & updates", 12, 6), ("Documents & notes", 18, 3)]


def nid():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=24))


def repo(name, provider, identifier, icon, prefix="", precision=3):
    return {"id": name.lower().replace(" ", "-"), "provider": provider, "identifier": identifier, "name": name,
            "iconUrl": GH.format(icon), "versionFilter": {"prefix": prefix, "precision": precision}}


# Latest release of everything homelab-apps pins, to compare with the compose files. Docker Hub
# wherever the project publishes there; GitHub only for Homarr and Arcane, as anonymous GitHub
# allows 60 requests an hour.
RELEASES = {
    "newReleaseWithin": "1w", "staleReleaseWithin": "6M", "showOnlyHighlighted": False, "showDetails": True,
    "showOnlyIcon": False, "topReleases": 0,
    "repositories": [
        repo("Homarr", "github", "homarr-labs/homarr", "homarr", "v"),
        repo("Arcane", "github", "getarcaneapp/arcane", "arcane", "v"),
        repo("Paperless", "dockerHub", "paperlessngx/paperless-ngx", "paperless-ngx"),
        repo("nebula-sync", "dockerHub", "lovelaze/nebula-sync", "pi-hole", "v"),
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
# One card per machine from Beszel (hub on prdsrv3); glazzed.css makes each machine its own card.
SERVER_GRID = {"statusFilter": "all", "showCpu": True, "showMemory": True, "showDisk": True, "showGpu": False,
               "showLoadAvg": True, "showNet": True, "showTemp": False, "showBattery": False, "showServices": False,
               "showUptime": True, "showAgent": False}
# Charts for the two physical hosts (Beszel system ids). A hub rebuilt from nothing gives every
# machine a new id: read them from beszel.example.com (a system's page address) and update these.
HOST_HISTORY = {"prx1": "03hzcypegtkki1k", "prx2": "ovs2248dq83evvn"}
NO_TITLE = {"title": None, "customCssClasses": [], "borderColor": ""}


def history(system_id):
    return {"systemId": system_id, "timePeriod": "24h", "showCpu": True, "showMemory": True, "showDisk": False,
            "showDiskIO": True, "showNetwork": True, "showDockerCpu": False, "showDockerMemory": False,
            "showDockerNetwork": False}


login()
spec = tomllib.loads((Path(__file__).resolve().parent.parent / "apps.toml").read_text())
b = query("board.getBoardByName", {"name": "Homelab"})
BASE = next(lay["id"] for lay in b["layouts"] if lay["role"] == "base")
MOBILE = next(lay["id"] for lay in b["layouts"] if lay["role"] == "mobile")
top = next(s for s in b["sections"] if s["kind"] == "empty" and s.get("xOffset", 0) == 0)["id"]
ints = {i["name"]: i["id"] for i in query("integration.all")}

# 1. Apps: create or update every app in apps.toml, so Homarr matches the file
changes = []
apps = {a["name"]: a for a in query("app.all")}
for entry in spec["tile"] + spec.get("off_board", []):
    icon = entry["icon"] if entry["icon"].startswith("https://") else ICON.format(entry["icon"])
    want = {"name": entry["name"], "description": entry.get("description", ""), "iconUrl": icon,
            "href": entry["href"], "pingUrl": entry.get("ping")}
    have = apps.get(entry["name"])
    if not have:
        changes.append(f"new app {entry['name']}")
        if not DRY:
            mutate("app.create", want)
    elif any((have.get(k) or "") != (v or "") for k, v in want.items()):
        changes.append(f"update app {entry['name']}")
        if not DRY:
            mutate("app.update", {**want, "id": have["id"]})
apps = {a["name"]: a["id"] for a in query("app.all")} if not DRY else {n: a["id"] for n, a in apps.items()}
app_name = {v: k for k, v in apps.items()}
tiles = {}
for entry in spec["tile"]:
    tiles.setdefault(entry["group"], []).append(entry["name"])

# 2. Sections: the containers, Base positions from GROUPS; Mobile keeps its own
by_title = {s["options"]["title"]: s for s in b["sections"] if s["kind"] == "container"}
mobile_bottom = {}


def mobile_slot(section_id, height):
    """Next free row at the bottom of a section in the Mobile layout."""
    used = [lay["yOffset"] + lay["height"] for s in b["sections"] for lay in s.get("layouts", [])
            if lay["layoutId"] == MOBILE and lay.get("parentSectionId") == section_id]
    used += [lay["yOffset"] + lay["height"] for i in b["items"] for lay in i["layouts"]
             if lay["layoutId"] == MOBILE and lay["sectionId"] == section_id]
    y = max([mobile_bottom.get(section_id, 0)] + used)
    mobile_bottom[section_id] = y + height
    return y


sections = [s for s in b["sections"] if s["kind"] == "empty"]
cid = {}
for title, y, h in GROUPS:
    s = by_title.get(title)
    if not s:
        changes.append(f"new container {title}")
        s = {"id": nid(), "kind": "container", "collapsed": False, "layouts": [],
             "options": {"title": title, "customCssClasses": ["hl-group"], "borderColor": "", "showLabel": True,
                         "collapsible": False, "showOpenAll": False, "scrollable": False}}
    mob = [lay for lay in s["layouts"] if lay["layoutId"] == MOBILE] or [
        {"layoutId": MOBILE, "parentSectionId": top, "xOffset": 0, "yOffset": mobile_slot(top, 6), "width": 3, "height": 6}]
    s["layouts"] = [{"layoutId": BASE, "parentSectionId": top, "xOffset": 0, "yOffset": y, "width": 12, "height": h}] + mob
    cid[title] = s["id"]
    sections.append(s)

# 3. Items: tiles from apps.toml, the widgets; anything else on the board is kept where it is
items = []
on_board = {n for names in tiles.values() for n in names}
for it in b["items"]:
    if it["kind"] == "app" and app_name.get(it["options"].get("appId")) not in on_board:
        changes.append(f"remove tile {app_name.get(it['options'].get('appId'), '?')}")
        continue
    items.append(it)
shown = {app_name.get(i["options"].get("appId")) for i in items if i["kind"] == "app"}
for name in sorted(on_board - shown):
    changes.append(f"add tile {name}")
    items.append({"id": nid(), "kind": "app", "options": {"appId": apps.get(name, name)}, "integrationIds": [],
                  "advancedOptions": dict(NO_TITLE), "layouts": []})
for host, sid in HOST_HISTORY.items():
    if not any(i["kind"] == "beszelSystemStats" and i["options"].get("systemId") == sid for i in items):
        items.append({"id": nid(), "kind": "beszelSystemStats", "options": history(sid), "integrationIds": [ints["Beszel"]],
                      "advancedOptions": dict(NO_TITLE), "layouts": []})
for kind, integration, opts in (("beszelSystemGrid", "Beszel", SERVER_GRID), ("releases", None, RELEASES)):
    if not any(i["kind"] == kind for i in items):
        items.append({"id": nid(), "kind": kind, "options": dict(opts), "integrationIds": [ints[integration]] if integration else [],
                      "advancedOptions": dict(NO_TITLE), "layouts": []})


def place(it, section, x, y, w, h):
    mob = [lay for lay in it["layouts"] if lay["layoutId"] == MOBILE and lay["sectionId"] == section] or [
        {"layoutId": MOBILE, "sectionId": section, "xOffset": 0, "yOffset": mobile_slot(section, h), "width": 3, "height": h}]
    it["layouts"] = [{"layoutId": BASE, "sectionId": section, "xOffset": x, "yOffset": y, "width": w, "height": h}] + mob


for it in items:
    k = it["kind"]
    if k == "app":
        name = app_name.get(it["options"]["appId"], it["options"]["appId"])
        it["options"].update(layout="row", showTitle=True, openInNewTab=True, pingEnabled=True,
                             descriptionDisplayMode="tooltip")
        group = next(g for g, names in tiles.items() if name in names)
        w = 12 // len(tiles[group])
        place(it, cid[group], tiles[group].index(name) * w, 0, w, 1)
    elif k == "clock":
        place(it, top, 0, 0, 3, 2)
    elif k == "weather":
        place(it, top, 3, 0, 3, 2)
    elif k == "uptimeKuma":
        place(it, top, 6, 0, 3, 2)
    elif k == "dnsHoleSummary":
        place(it, top, 9, 0, 3, 2)
    elif k == "beszelSystemGrid":
        it["options"] = it["options"] or dict(SERVER_GRID)  # defaults for a new widget; your edits in Homarr stay
        place(it, cid["Servers"], 0, 0, 12, 3)
    elif k == "beszelSystemStats":
        place(it, cid["Host history"], list(HOST_HISTORY.values()).index(it["options"]["systemId"]) * 6, 0, 6, 4)
    elif k == "dockerContainers":
        place(it, cid["Containers & updates"], 0, 0, 8, 6)
    elif k == "releases":
        it["options"]["repositories"] = RELEASES["repositories"]  # the list follows homelab-apps; other settings stay
        it["options"] = {**RELEASES, **it["options"]}
        place(it, cid["Containers & updates"], 8, 0, 4, 6)
    elif k == "paperlessNgx":
        place(it, cid["Documents & notes"], 0, 0, 6, 3)
    elif k == "notebook":
        place(it, cid["Documents & notes"], 6, 0, 6, 3)
    # any other item (added by hand in Homarr) keeps its layouts as they are

print("\n".join(changes) or "apps and tiles already match apps.toml")
if DRY:
    print(f"(dry run: {len(sections)} sections, {len(items)} items, nothing saved)")
    sys.exit(0)
mutate("board.saveBoard", {"id": b["id"], "sections": sections, "items": items})
print(f"layout saved: {len(GROUPS)} groups, {len(items)} items; set the look with apply_theme.py")
