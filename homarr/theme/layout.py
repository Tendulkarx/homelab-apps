#!/usr/bin/env python3
"""Lay out the Homelab board. Run on prdsrv1 next to homarr_session.py (see README.md).

One plain section holds everything. Headed groups are Homarr "dynamic" sections: titled frames
that never collapse. Every service is an app tile in the same compact style (name left, icon
right, description on hover). Also applies the CSS and logo in this folder.
"""
import base64
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


# A GitHub tile completes the Monitoring & network row
apps = {a["name"]: a["id"] for a in query("app.all")}
if "GitHub" not in apps:
    mutate("app.create", {"name": "GitHub", "description": "proxmox-lab, homelab-apps, property-search",
                          "iconUrl": "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/github.svg",
                          "href": "https://github.com/Tendulkarx?tab=repositories", "pingUrl": None})
    apps = {a["name"]: a["id"] for a in query("app.all")}
app_name = {v: k for k, v in apps.items()}

# Headed groups: (title, 20 characters at most; y; height), full width in the plain section
GROUPS = [("Apps", 2, 1), ("Monitoring & network", 3, 1), ("Servers", 4, 6), ("Containers & docs", 10, 6)]
old_dyn = {s["options"]["title"]: s["id"] for s in b["sections"] if s["kind"] == "dynamic"}
dyn = {title: old_dyn.get(title) or nid() for title, *_ in GROUPS}
sections = [{"id": top, "kind": "empty", "xOffset": 0, "yOffset": 0}] + [
    {"id": dyn[t], "kind": "dynamic", "options": {"title": t, "customCssClasses": ["hl-group"], "borderColor": ""},
     "layouts": [{"layoutId": L, "parentSectionId": top, "xOffset": 0, "yOffset": y, "width": 12, "height": h}]}
    for t, y, h in GROUPS]

TILES = {
    "Apps": ["Paperless", "n8n", "Metabase", "House Hunting", "Logs", "Arcane"],
    "Monitoring & network": ["Uptime Kuma", "Status page", "Pi-hole", "UniFi", "Cloudflare", "GitHub"],
}
SERVER_TILES = ["prx1", "prx2", "Backup Server"]

items = b["items"]
if not any(i["kind"] == "app" and app_name.get(i["options"].get("appId")) == "GitHub" for i in items):
    items.append({"id": nid(), "kind": "app", "options": {"appId": apps["GitHub"]}, "integrationIds": [],
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
                at(it, dyn[group], names.index(name) * 2, 0, 2, 1)
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
    elif k == "dnsHoleControls":
        at(it, dyn["Servers"], 6, 4, 6, 2)
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

logo = "data:image/svg+xml;base64," + base64.b64encode(open("logo.svg", "rb").read()).decode()
mutate("board.savePartialBoardSettings", {"id": b["id"], "customCss": open("dashboard.css").read(),
                                           "logoImageUrl": logo, "faviconImageUrl": logo, "opacity": 55})
print("theme applied")
