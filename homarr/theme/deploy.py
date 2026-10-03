#!/usr/bin/env python3
"""Apply the whole board in one go, with one Touch ID prompt: python3 deploy.py [--dry-run]

Runs apply_theme.py (look, branding, header), widgets.py (custom widgets) and layout.py (tiles,
containers, positions) in this one process, so the Homarr API key is read from 1Password once.
--dry-run is passed to widgets.py and layout.py; the theme is applied either way (it is idempotent).
"""
import os
import runpy
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
os.chdir(here)
sys.path.insert(0, str(here))
args = sys.argv[1:]
for script in ("apply_theme.py", "widgets.py", "layout.py"):
    print(f"\n### {script}")
    sys.argv = [script] + (["glazzed"] if script == "apply_theme.py" else args)
    runpy.run_path(str(here / script), run_name="__main__")
