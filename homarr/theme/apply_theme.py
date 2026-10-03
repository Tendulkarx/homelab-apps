#!/usr/bin/env python3
"""Apply a theme to the whole Homarr instance: python3 apply_theme.py [glazzed|bluematrix]

Homarr 2's instance branding carries the look everywhere, sign-in page included: the name, the
`>_` logo (logo.svg, uploaded once to Homarr's media store) as logo and favicon, the colours,
the corner style and the theme as global CSS. The Homelab board keeps only its own settings
(opacity, item radius, colours) and no CSS of its own, so the theme lives in one place. The
owner's header gets a Docker button (Homarr's default header otherwise).
"""
import json
import sys

from homarr_session import login, mutate, query, upload

THEMES = {
    "glazzed": {"css": "glazzed.css", "primaryColor": "#2d8cf0", "secondaryColor": "#4cd964", "opacity": 50, "itemRadius": "lg"},
    "bluematrix": {"css": "bluematrix.css", "primaryColor": "#00b0ff", "secondaryColor": "#00ff9c", "opacity": 55, "itemRadius": "lg"},
}
LOGO = "homelab-logo.svg"

name = sys.argv[1] if len(sys.argv) > 1 else "glazzed"
t = THEMES[name]
login()

# The logo: reuse the copy already uploaded, else upload logo.svg
found = query("media.getPaginated", {"page": 1, "pageSize": 10, "search": LOGO, "includeFromAllUsers": True})
media = next((m["id"] for m in found.get("items", []) if m.get("name") == LOGO), None)
if not media:
    media = upload(LOGO, open("logo.svg", "rb").read(), "image/svg+xml")
    print(f"logo uploaded ({media})")
logo = f"/api/user-medias/{media}"

mutate("serverSettings.saveSettings", {"settingsKey": "branding", "value": {
    "appName": "Homelab", "greeting": "", "logoImageUrl": logo, "faviconImageUrl": logo,
    "primaryColor": t["primaryColor"], "secondaryColor": t["secondaryColor"], "lockPrimaryColor": False,
    "defaultRadius": t["itemRadius"], "customCss": open(t["css"]).read(),
    "authBranding": {"showAppName": True, "showLogo": True, "showGreeting": False},
}})
b = query("board.getBoardByName", {"name": "Homelab"})
mutate("board.savePartialBoardSettings", {"id": b["id"], "customCss": "", "primaryColor": t["primaryColor"],
       "secondaryColor": t["secondaryColor"], "opacity": t["opacity"], "itemRadius": t["itemRadius"],
       "logoImageUrl": logo, "faviconImageUrl": logo})
# Header (per user; the board's owner): Homarr's default plus a Docker button for the containers
# on all three hosts. Kept: logo, search, edit, settings, account.
owner = query("user.getById", {"userId": b["creatorId"]})
prefs = owner.get("headerPreferences") or ""
prefs = json.loads(prefs) if isinstance(prefs, str) and prefs else prefs or {
    "version": 3, "visible": True, "searchDisplay": "input", "logoDisplay": "logoAndText",
    "zones": {"left": [{"type": "builtin", "id": "logo"}], "center": [{"type": "builtin", "id": "search"}],
              "right": [{"type": "builtin", "id": i} for i in ("boardEdit", "boardSettings", "user")]}}
right = prefs["zones"]["right"]
if not any(i.get("type") == "builtin" and i.get("id") == "docker" for z in prefs["zones"].values() for i in z):
    right.insert(max(0, len(right) - 1), {"type": "builtin", "id": "docker"})  # before the account menu
    mutate("user.changeHeaderPreferences", {"id": owner["id"], "headerPreferences": prefs})
    print("header: Docker button added")
print(f"theme {name} applied to the instance (global CSS, logo, colours); board CSS cleared")
