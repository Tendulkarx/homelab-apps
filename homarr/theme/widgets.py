#!/usr/bin/env python3
"""Deploy the custom widgets in ../widgets/*.json to Homarr. Run on the Mac; Touch ID once.

  python3 widgets.py              preview, test every query, then save (create or update)
  python3 widgets.py --dry-run    preview and test only, save nothing
  python3 widgets.py backups      only ../widgets/backups.json

Follows Homarr 2's Custom Widget lifecycle: customWidget.previewCreate validates the manifest
and JSX, previewQuery runs each query once against the real service (evidence Homarr requires
before saving), then createFromPreview or updateFromPreview. Sources name a saved integration
(`integrationName`); this resolves it to its id, so the files carry no ids or credentials.
Placing a widget on the board is layout.py's job (WIDGETS there).
"""
import json
import sys
from pathlib import Path

from homarr_session import login, mutate, query

DRY = "--dry-run" in sys.argv
only = [a for a in sys.argv[1:] if not a.startswith("--")]
folder = Path(__file__).resolve().parent.parent / "widgets"


def result(r):
    return r["result"]["data"]["json"]


login()
integrations = {i["name"]: i for i in query("integration.all")}
existing = {w["name"]: w["id"] for w in query("customWidget.list")}

for path in sorted(folder.glob("*.json")):
    if only and path.stem not in only:
        continue
    definition = json.loads(path.read_text())
    definition.pop("$comment", None)
    definition["template"] = "\n".join(definition.pop("templateLines"))
    for sid, source in definition["sources"].items():
        name = source.pop("integrationName", None)
        if name:
            if name not in integrations:
                raise SystemExit(f"{path.name}: source {sid}: no integration named {name!r}")
            source["integrationId"] = integrations[name]["id"]
    def_id = existing.get(definition["name"])
    print(f"== {definition['name']} ({'update' if def_id else 'new'})")
    preview = result(mutate("customWidget.previewCreate", {"definition": definition, "secrets": [],
                                                            **({"definitionId": def_id} if def_id else {})}))
    if not preview.get("success"):
        raise SystemExit(json.dumps(preview, indent=1)[:2000])
    session = preview["previewSession"]["id"]
    failed = False
    for q in preview.get("queries", []):
        rid = q["requestId"] if isinstance(q, dict) else q
        r = query("customWidget.previewQuery", {"sessionId": session, "requestId": rid})
        ok = r.get("ok", r.get("status") == 200)
        failed |= not ok
        sample = json.dumps(r.get("data"))[:160]
        print(f"  query {rid}: {'OK' if ok else 'FAILED'} (HTTP {r.get('status')}) {sample}")
    if failed:
        raise SystemExit("  a query failed: nothing saved")
    if DRY:
        print("  dry run: tested, not saved")
        continue
    if def_id:
        saved = result(mutate("customWidget.updateFromPreview", {"previewSessionId": session, "definitionId": def_id}))
    else:
        saved = result(mutate("customWidget.createFromPreview", {"previewSessionId": session, "targetBoardId": None}))
    print(f"  saved: {json.dumps(saved)[:200]}")
