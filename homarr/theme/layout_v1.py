#!/usr/bin/env python3
"""Arrange the Homelab board into sections and give it the Blue Matrix look. Run on prdsrv1."""
import random
import string

from hs import login, query, mutate, opener, BASE
import json
import urllib.request

login()
b = query("board.getBoardByName", {"name": "Homelab"})
layout_id = b["layouts"][0]["id"]
apps = {a["id"]: a["name"] for a in query("app.all")}


def new_id():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=24))


top = next(s for s in b["sections"] if s["kind"] == "empty" and s["yOffset"] == 0)
cat = {name: new_id() for name in ("Apps", "Infrastructure", "Containers & documents")}
sections = [
    {"id": top["id"], "kind": "empty", "xOffset": 0, "yOffset": 0},
    {"id": cat["Apps"], "kind": "category", "name": "Apps", "xOffset": 0, "yOffset": 1, "collapsed": False},
    {"id": new_id(), "kind": "empty", "xOffset": 0, "yOffset": 2},
    {"id": cat["Infrastructure"], "kind": "category", "name": "Infrastructure", "xOffset": 0, "yOffset": 3, "collapsed": False},
    {"id": new_id(), "kind": "empty", "xOffset": 0, "yOffset": 4},
    {"id": cat["Containers & documents"], "kind": "category", "name": "Containers & documents", "xOffset": 0, "yOffset": 5, "collapsed": False},
    {"id": new_id(), "kind": "empty", "xOffset": 0, "yOffset": 6},
]

# section, x, y, width, height (12 columns; cells are roughly square)
PLACE = {
    "clock": (top["id"], 0, 0, 3, 2),
    "weather": (top["id"], 3, 0, 3, 2),
    "uptimeKuma": (top["id"], 6, 0, 3, 2),
    "dnsHoleSummary": (top["id"], 9, 0, 3, 2),
    "healthMonitoring": (cat["Infrastructure"], 0, 0, 8, 4),
    "dnsHoleControls": (cat["Infrastructure"], 8, 0, 4, 2),
    "notebook": (cat["Infrastructure"], 8, 2, 4, 2),
    "dockerContainers": (cat["Containers & documents"], 0, 0, 8, 5),
    "paperlessNgx": (cat["Containers & documents"], 8, 0, 4, 3),
}
MAIN_APPS = ["Paperless", "n8n", "Metabase", "House Hunting", "Uptime Kuma", "Status page", "Logs", "Arcane"]
INFRA_APPS = ["Pi-hole", "prx1", "prx2", "Backup Server", "UniFi", "Cloudflare"]
for i, name in enumerate(MAIN_APPS):
    PLACE[name] = (cat["Apps"], (i % 4) * 3, i // 4, 3, 1)
for i, name in enumerate(INFRA_APPS):
    PLACE[name] = (cat["Infrastructure"], i * 2, 4, 2, 1)

items = []
for it in b["items"]:
    key = apps.get(it["options"].get("appId")) if it["kind"] == "app" else it["kind"]
    if key not in PLACE:
        raise SystemExit(f"no place for {key}")
    sec, x, y, w, h = PLACE[key]
    opts = dict(it["options"])
    if it["kind"] == "app":
        opts.update(layout="row", showTitle=True, openInNewTab=True, pingEnabled=True,
                    descriptionDisplayMode="normal" if key in MAIN_APPS else "tooltip")
    items.append({"id": it["id"], "kind": it["kind"], "options": opts, "integrationIds": it["integrationIds"],
                  "advancedOptions": it["advancedOptions"],
                  "layouts": [{"layoutId": layout_id, "sectionId": sec, "xOffset": x, "yOffset": y, "width": w, "height": h}]})
mutate("board.saveBoard", {"id": b["id"], "sections": sections, "items": items})
print(f"layout saved: {len(sections)} sections, {len(items)} items")

CSS = open("dashboard.css").read()
mutate("board.savePartialBoardSettings", {
    "id": b["id"], "pageTitle": "Homelab", "metaTitle": "Homelab", "primaryColor": "#00b0ff",
    "secondaryColor": "#00ff9c", "opacity": 60, "itemRadius": "lg", "customCss": CSS,
    "backgroundImageUrl": None, "disableStatus": False})
print(f"theme saved: Blue Matrix colours, glass cards, custom CSS {len(CSS)} chars")

req = urllib.request.Request(BASE + "/api/trpc/user.changeColorScheme", data=json.dumps({"json": {"colorScheme": "dark"}}).encode(),
                             headers={"Content-Type": "application/json"})
try:
    opener.open(req)
    print("colour scheme: dark")
except Exception as e:
    print("colour scheme: set it in your user menu (", e, ")")
