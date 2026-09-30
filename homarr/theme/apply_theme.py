#!/usr/bin/env python3
"""Apply a theme to the Homelab board: python3 apply_theme.py [glazzed|bluematrix]."""
import base64
import sys

from homarr_session import login, mutate, query

THEMES = {
    "glazzed": {"css": "glazzed.css", "primaryColor": "#2d8cf0", "secondaryColor": "#4cd964", "opacity": 50, "itemRadius": "lg"},
    "bluematrix": {"css": "bluematrix.css", "primaryColor": "#00b0ff", "secondaryColor": "#00ff9c", "opacity": 55, "itemRadius": "lg"},
}
name = sys.argv[1] if len(sys.argv) > 1 else "glazzed"
t = THEMES[name]
login()
b = query("board.getBoardByName", {"name": "Homelab"})
logo = "data:image/svg+xml;base64," + base64.b64encode(open("logo.svg", "rb").read()).decode()
mutate("board.savePartialBoardSettings", {"id": b["id"], "customCss": open(t["css"]).read(), "primaryColor": t["primaryColor"],
       "secondaryColor": t["secondaryColor"], "opacity": t["opacity"], "itemRadius": t["itemRadius"],
       "logoImageUrl": logo, "faviconImageUrl": logo})
print(f"theme {name} applied")
