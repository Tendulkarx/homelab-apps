import random, string
from hs import login, query, mutate
login()
b = query("board.getBoardByName", {"name": "Homelab"})
L = b["layouts"][0]["id"]
apps = {a["id"]: a["name"] for a in query("app.all")}
ints = {i["name"]: i["id"] for i in query("integration.all")}
sec = {s.get("name") or ("top" if s["yOffset"] == 0 else s["id"]): s["id"] for s in b["sections"]}
top, APPS, INFRA, CONT = sec["top"], sec["Apps"], sec["Infrastructure"], sec["Containers & documents"]

def nid(): return "".join(random.choices(string.ascii_lowercase + string.digits, k=24))

items = b["items"]
health = [i for i in items if i["kind"] == "healthMonitoring"]
h1 = health[0]
h1["integrationIds"] = [ints["Proxmox prx1"]]
h1["advancedOptions"]["title"] = "prx1 · prdsrv1, prdsrv2, tstsrv1"
if len(health) == 1:
    h2 = {"id": nid(), "kind": "healthMonitoring", "options": dict(h1["options"]), "integrationIds": [ints["Proxmox prx2"]],
          "advancedOptions": {"title": "prx2 · prdsrv3, Backup Server", "customCssClasses": [], "borderColor": ""}, "layouts": []}
    items.append(h2)
else:
    h2 = health[1]
    h2["integrationIds"] = [ints["Proxmox prx2"]]
    h2["advancedOptions"]["title"] = "prx2 · prdsrv3, Backup Server"

INFRA_APPS = ["Pi-hole", "prx1", "prx2", "Backup Server", "UniFi", "Cloudflare"]
def place(it, s, x, y, w, h):
    it["layouts"] = [{"layoutId": L, "sectionId": s, "xOffset": x, "yOffset": y, "width": w, "height": h}]
for it in items:
    k = it["kind"]
    name = apps.get(it["options"].get("appId")) if k == "app" else None
    if it is h1: place(it, INFRA, 0, 0, 6, 4)
    elif it is h2: place(it, INFRA, 6, 0, 6, 4)
    elif name in INFRA_APPS: place(it, INFRA, INFRA_APPS.index(name) * 2, 4, 2, 1)
    elif k == "dnsHoleControls":
        place(it, INFRA, 0, 5, 4, 2); it["advancedOptions"]["title"] = "Pi-hole controls"
    elif k == "notebook": place(it, INFRA, 4, 5, 8, 2)
    elif k == "dnsHoleSummary": it["options"]["usePiHoleColors"] = False
    elif k == "dockerContainers": place(it, CONT, 0, 0, 8, 6); it["advancedOptions"]["title"] = "Containers · prdsrv1, prdsrv2, prdsrv3"
    elif k == "paperlessNgx": place(it, CONT, 8, 0, 4, 3)
mutate("board.saveBoard", {"id": b["id"], "sections": [{k: v for k, v in s.items() if k not in ("items",)} for s in b["sections"]], "items": items})
print("layout saved:", len(items), "items")
mutate("board.savePartialBoardSettings", {"id": b["id"], "customCss": open("dashboard.css").read(),
       "logoImageUrl": open("logo.uri").read(), "faviconImageUrl": open("logo.uri").read(), "opacity": 55})
print("theme updated")
for s in b["sections"]:
    if s["kind"] == "category":
        mutate("section.changeCollapsed", {"sectionId": s["id"], "collapsed": False})
print("categories expanded")
