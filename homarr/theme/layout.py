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
# Base positions are written in 12-column units; SCALE turns them into the real grid. SCALE 2
# (24 columns) was tried on 2026-10-03 and dropped: Homarr zooms a 24-column board to a third,
# and widgets that do not compensate (app names, Uptime Kuma, Paperless) became unreadable.
SCALE = 1


def g(v):
    """12-column units to grid cells."""
    return int(round(v * SCALE))


# Headed groups top to bottom, below the top row (2 high): (title, height), 12-column units.
# "Overview" (clock, weather, Uptime Kuma, Pi-hole) is a container with no heading: every row is
# then a container with the same inner grid, so card edges line up across the board (a container's
# grid is narrower than the plain section's, which left the top row 10px wider).
UNLABELLED = {"Overview"}
# Mobile heights that must be at least this (rows), e.g. five server cards stacked two by two.
# Anything below a container that grows moves down by the same amount.
MOBILE_MIN = {"Servers": 4}
GROUPS = [("Overview", 2), ("Apps", 1), ("Monitoring & network", 1), ("Infrastructure", 1), ("Servers", 3), ("Backups & jobs", 1),
          ("Host history", 4), ("Containers & updates", 6), ("Documents & notes", 3)]
TOP_ROW = 0
# Extra desktop layouts (Homarr 2 breakpoints) and the heights where they differ from Base. None:
# a "Wide" layout with a half-height Backups & jobs row needed the 24-column grid (see SCALE).
EXTRA_LAYOUTS = []
HEIGHTS = {}


def group_y(layout_name):
    """Each group's (y, height) in one desktop layout, stacked top to bottom."""
    out, y = {}, TOP_ROW
    for title, h in GROUPS:
        h = HEIGHTS.get(layout_name, {}).get(title, h)
        out[title] = (y, h)
        y += h
    return out


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
# No sidebar (a right rail was tried on 2026-10-03 and dropped): Base is 12 columns, no rails.
RAIL_COLUMNS = 0
NO_TITLE = {"title": None, "customCssClasses": [], "borderColor": ""}
# Custom widgets (../widgets/*.json, deployed by widgets.py):
#   name: (group, x, y, width, height or {layout: height}, height on Mobile)
WIDGETS = {"Backups": ("Backups & jobs", 0, 0, 12, 1, 2)}


def history(system_id):
    return {"systemId": system_id, "timePeriod": "24h", "showCpu": True, "showMemory": True, "showDisk": False,
            "showDiskIO": True, "showNetwork": True, "showDockerCpu": False, "showDockerMemory": False,
            "showDockerNetwork": False}


login()
spec = tomllib.loads((Path(__file__).resolve().parent.parent / "apps.toml").read_text())
b = query("board.getBoardByName", {"name": "Homelab"})
COLS = 12 * SCALE + RAIL_COLUMNS
layouts = [dict(lay) for lay in b["layouts"]]
want_layouts = False
for lay in layouts:
    if lay["role"] in ("base", "custom") and (lay["columnCount"], lay["rightGutterColumnCount"]) != (COLS, RAIL_COLUMNS):
        print(f"{lay['name']} layout: {lay['columnCount']} columns -> {COLS}")
        lay.update(columnCount=COLS, rightGutterColumnCount=RAIL_COLUMNS, leftGutterColumnCount=0)
        want_layouts = True
for extra in EXTRA_LAYOUTS:
    if not any(lay["name"] == extra["name"] for lay in layouts):
        print(f"new layout {extra['name']} from {extra['breakpoint']}px")
        layouts.append({"id": nid(), "name": extra["name"], "columnCount": COLS, "leftGutterColumnCount": 0,
                        "rightGutterColumnCount": RAIL_COLUMNS, "breakpoint": extra["breakpoint"], "role": "custom"})
        want_layouts = True
for lay in [lay for lay in layouts if lay["role"] == "custom" and lay["name"] not in {e["name"] for e in EXTRA_LAYOUTS}]:
    print(f"remove layout {lay['name']}")
    layouts.remove(lay)
    want_layouts = True
if want_layouts and not DRY:
    mutate("board.saveLayouts", {"id": b["id"], "layouts": layouts})
    b = query("board.getBoardByName", {"name": "Homelab"})
BASE = next(lay["id"] for lay in b["layouts"] if lay["role"] == "base")
DESKTOP = [(lay["id"], "Base" if lay["role"] == "base" else lay["name"]) for lay in b["layouts"] if lay["role"] != "mobile"]
MOBILE = next(lay["id"] for lay in b["layouts"] if lay["role"] == "mobile")
top = next(s for s in b["sections"] if s["kind"] == "empty" and s.get("xOffset", 0) == 0)["id"]
ints = {i["name"]: i["id"] for i in query("integration.all")}
custom = {w["name"]: w for w in query("customWidget.list") if w["name"] in WIDGETS}
for name in WIDGETS:
    if name not in custom:
        print(f"custom widget {name} not deployed yet: run widgets.py first; skipped")

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
overview_mobile = {}
for title, _ in GROUPS:
    s = by_title.get(title)
    if not s:
        changes.append(f"new container {title}")
        s = {"id": nid(), "kind": "container", "collapsed": False, "layouts": [],
             "options": {"title": title, "customCssClasses": ["hl-group"], "borderColor": "", "showLabel": True,
                         "collapsible": False, "showOpenAll": False, "scrollable": False}}
    s["options"]["showLabel"] = title not in UNLABELLED
    mob = [lay for lay in s["layouts"] if lay["layoutId"] == MOBILE]
    if not mob and title == "Overview":
        # On Mobile it takes the space its four widgets already use at the top of the board
        tops = [lay for i in b["items"] if i["kind"] in ("clock", "weather", "uptimeKuma", "dnsHoleSummary")
                for lay in i["layouts"] if lay["layoutId"] == MOBILE and lay["sectionId"] == top]
        y0 = min((lay["yOffset"] for lay in tops), default=0)
        overview_mobile = {"y0": y0}
        mob = [{"layoutId": MOBILE, "parentSectionId": top, "xOffset": 0, "yOffset": y0, "width": 3,
                "height": max((lay["yOffset"] + lay["height"] for lay in tops), default=y0 + 6) - y0}]
    mob = mob or [{"layoutId": MOBILE, "parentSectionId": top, "xOffset": 0, "yOffset": mobile_slot(top, 6), "width": 3, "height": 6}]
    s["layouts"] = [{"layoutId": lid, "parentSectionId": top, "xOffset": 0, "yOffset": g(group_y(name)[title][0]),
                     "width": g(12), "height": g(group_y(name)[title][1])} for lid, name in DESKTOP] + mob
    cid[title] = s["id"]
    sections.append(s)

# Mobile minimum heights: grow the container, then move whatever is below it down to match
for title, rows in MOBILE_MIN.items():
    s = next(x for x in sections if x.get("options", {}).get("title") == title)
    mob = next(lay for lay in s["layouts"] if lay["layoutId"] == MOBILE)
    grow = rows - mob["height"]
    if grow > 0:
        changes.append(f"Mobile: {title} {mob['height']} -> {rows} rows")
        for other in sections:
            for lay in other.get("layouts", []):
                if lay["layoutId"] == MOBILE and lay.get("parentSectionId") == top and lay["yOffset"] > mob["yOffset"]:
                    lay["yOffset"] += grow
        for it in b["items"]:
            for lay in it["layouts"]:
                if lay["layoutId"] == MOBILE and lay["sectionId"] == top and lay["yOffset"] > mob["yOffset"]:
                    lay["yOffset"] += grow
        mob["height"] = rows
        MOBILE_GROWN = globals().setdefault("MOBILE_GROWN", {}); MOBILE_GROWN[s["id"]] = rows

# 3. Items: tiles from apps.toml, the widgets; anything else on the board is kept where it is
items = []
on_board = {n for names in tiles.values() for n in names}
for it in b["items"]:
    if it["kind"] == "beszelSystemTable":  # the sidebar's server table, now gone
        changes.append("remove the sidebar server table")
        continue
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


for name, w in custom.items():
    if not any(i["kind"] == "customApi" and i["options"].get("definitionId") == w["id"] for i in items):
        changes.append(f"add custom widget {name}")
        items.append({"id": nid(), "kind": "customApi", "integrationIds": [], "advancedOptions": dict(NO_TITLE), "layouts": [],
                      "options": {"definitionId": w["id"], "configuration": {}, "configurationVersion": 0}})


def overview(it, x):
    """A top-row widget in the Overview container; on Mobile it keeps its place, now inside it."""
    for lay in it["layouts"]:
        if lay["layoutId"] == MOBILE and lay["sectionId"] == top:
            lay["sectionId"] = cid["Overview"]
            lay["yOffset"] -= overview_mobile.get("y0", 0)
    place(it, cid["Overview"], x, 0, 3, 2)


def place(it, section, x, y, w, h):
    """Position in every desktop layout, in 12-column units (h may be {layout: height}); Mobile keeps
    its own, or gets the next free row."""
    hs = h if isinstance(h, dict) else {}
    base_h = hs.get("Base", h if not isinstance(h, dict) else 1)
    mh = max(1, int(round(base_h)))
    mob = [lay for lay in it["layouts"] if lay["layoutId"] == MOBILE and lay["sectionId"] == section] or [
        {"layoutId": MOBILE, "sectionId": section, "xOffset": 0, "yOffset": mobile_slot(section, mh), "width": 3, "height": mh}]
    it["layouts"] = [{"layoutId": lid, "sectionId": section, "xOffset": g(x), "yOffset": g(y), "width": g(w),
                      "height": g(hs.get(name, base_h))} for lid, name in DESKTOP] + mob


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
        overview(it, 0)
    elif k == "weather":
        overview(it, 3)
    elif k == "uptimeKuma":
        overview(it, 6)
    elif k == "dnsHoleSummary":
        overview(it, 9)
    elif k == "beszelSystemGrid":
        it["options"] = it["options"] or dict(SERVER_GRID)  # defaults for a new widget; your edits in Homarr stay
        place(it, cid["Servers"], 0, 0, 12, 3)
        for lay in it["layouts"]:
            if lay["layoutId"] == MOBILE:
                lay["height"] = max(lay["height"], MOBILE_MIN["Servers"])
    elif k == "beszelSystemStats":
        place(it, cid["Host history"], list(HOST_HISTORY.values()).index(it["options"]["systemId"]) * 6, 0, 6, 4)
    elif k == "dockerContainers":
        place(it, cid["Containers & updates"], 0, 0, 8, 6)
    elif k == "releases":
        it["options"]["repositories"] = RELEASES["repositories"]  # the list follows homelab-apps; other settings stay
        it["options"] = {**RELEASES, **it["options"]}
        place(it, cid["Containers & updates"], 8, 0, 4, 6)
    elif k == "customApi":
        name = next((n for n, w in custom.items() if w["id"] == it["options"].get("definitionId")), None)
        if name:
            group, x, y, w, h, mobile_h = WIDGETS[name]
            place(it, cid[group], x, y, w, h)
            for lay in it["layouts"]:
                if lay["layoutId"] == MOBILE:
                    lay["height"] = mobile_h
    elif k == "paperlessNgx":
        place(it, cid["Documents & notes"], 0, 0, 6, 3)
    elif k == "notebook":
        place(it, cid["Documents & notes"], 6, 0, 6, 3)
    # any other item (added by hand in Homarr) keeps its layouts as they are

# Mobile: each container exactly as tall as what it holds, stacked in the desktop order
y = 0
for title, _ in GROUPS:
    s_ = next(x for x in sections if x.get("options", {}).get("title") == title)
    mob = next(lay for lay in s_["layouts"] if lay["layoutId"] == MOBILE)
    inside = [lay["yOffset"] + lay["height"] for it in items for lay in it["layouts"]
              if lay["layoutId"] == MOBILE and lay["sectionId"] == s_["id"]]
    height = max(inside) if inside else mob["height"]
    if (mob["yOffset"], mob["height"]) != (y, height):
        changes.append(f"Mobile: {title} at row {y}, {height} high")
    mob.update(yOffset=y, xOffset=0, height=height)
    y += height

print("\n".join(changes) or "apps and tiles already match apps.toml")
if DRY:
    print(f"(dry run: {len(sections)} sections, {len(items)} items, nothing saved)")
    sys.exit(0)
mutate("board.saveBoard", {"id": b["id"], "sections": sections, "items": items})
print(f"layout saved: {len(GROUPS)} groups, {len(items)} items, layouts {', '.join(n for _, n in DESKTOP)} and Mobile")
