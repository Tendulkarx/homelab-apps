#!/usr/bin/env python3
"""Apply a theme to the whole Homarr instance: python3 apply_theme.py [glazzed|bluematrix]

Homarr 2's instance branding carries the look everywhere, sign-in page included: the name, the
`>_` logo (logo.svg, uploaded once to Homarr's media store) as logo and favicon, the colours,
the corner style and the theme as global CSS. The Homelab board keeps only its own settings
(opacity, item radius, colours) and no CSS of its own, so the theme lives in one place.
"""
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
print(f"theme {name} applied to the instance (global CSS, logo, colours); board CSS cleared")
