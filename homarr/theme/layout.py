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

# Headed groups: (title, 20 characters at most; y; height), full width in the plain section
GROUPS = [("Apps", 2, 1), ("Monitoring & network", 3, 1), ("Servers", 4, 5), ("Containers & docs", 9, 6)]
old_dyn = {s["options"]["title"]: s["id"] for s in b["sections"] if s["kind"] == "dynamic"}
dyn = {title: old_dyn.get(title) or nid() for title, *_ in GROUPS}
sections = [{"id": top, "kind": "empty", "xOffset": 0, "yOffset": 0}] + [
    {"id": dyn[t], "kind": "dynamic", "options": {"title": t, "customCssClasses": ["hl-group"], "borderColor": ""},
     "layouts": [{"layoutId": L, "parentSectionId": top, "xOffset": 0, "yOffset": y, "width": 12, "height": h}]}
    for t, y, h in GROUPS]

# Each group is one balanced row: four wide tiles, or six narrow ones
TILES = {
    "Apps": ["Paperless", "n8n", "Metabase", "House Hunting"],
    "Monitoring & network": ["Uptime Kuma", "Status page", "Pi-hole", "Pi-hole 2", "UniFi", "Cloudflare"],
}
SERVER_TILES = ["prx1", "prx2", "Backup Server", "Off-site backups", "Arcane", "Logs"]

# Placed nowhere, so dropped from the board (the apps themselves are kept)
items = [i for i in b["items"] if i["kind"] != "dnsHoleControls"
         and not (i["kind"] == "app" and app_name.get(i["options"].get("appId")) == "GitHub")]
have = {app_name.get(i["options"].get("appId")) for i in items if i["kind"] == "app"}
for name in (n for n, *_ in EXTRA_APPS if n not in have):
    items.append({"id": nid(), "kind": "app", "options": {"appId": apps[name]}, "integrationIds": [],
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
        if name in SERVER_TILES:
            at(it, dyn["Servers"], SERVER_TILES.index(name) * 2, 4, 2, 1)
    elif k == "clock":
        at(it, top, 0, 0, 3, 2)
    elif k == "weather":
        at(it, top, 3, 0, 3, 2)
    elif k == "uptimeKuma":
        at(it, top, 6, 0, 3, 2)
    elif k == "dnsHoleSummary":
        at(it, top, 9, 0, 3, 2)
    elif k == "healthMonitoring":
        at(it, dyn["Servers"], 6 if ints["Proxmox prx2"] in it["integrationIds"] else 0, 0, 6, 4)
    elif k == "dockerContainers":
        at(it, dyn["Containers & docs"], 0, 0, 8, 6)
    elif k == "paperlessNgx":
        at(it, dyn["Containers & docs"], 8, 0, 4, 3)
    elif k == "notebook":
        at(it, dyn["Containers & docs"], 8, 3, 4, 3)
    if not it["layouts"]:
        raise SystemExit(f"no place for {k}")

mutate("board.saveBoard", {"id": b["id"], "sections": sections, "items": items})
print(f"layout saved: {len(GROUPS)} headed groups, {len(items)} items, no collapsible sections")

print("layout done; set the look with apply_theme.py")
