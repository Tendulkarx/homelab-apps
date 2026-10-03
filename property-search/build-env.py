#!/usr/bin/env python3
"""Build property-search's .env from 1Password, on the Mac, straight to prdsrv2:

    python3 build-env.py | ssh prdsrv2 'umask 077; cat > /opt/docker/property-search/.env.new'

Each KEY=op://... line in .env.example is read with `op read` (one Touch ID prompt); other
lines pass through. Values are double-quoted with \\, ", $ and newlines escaped, so the
multi-line Sheets JSON and passwords containing $ or quotes reach the container unchanged
(Compose env_file rules). Nothing is printed except the finished file, on stdout.
"""
import pathlib
import subprocess
import sys

example = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name(".env.example")


def quote(value: str) -> str:
    value = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "$$").replace("\n", "\\n")
    return f'"{value}"'


out = []
for line in example.read_text().splitlines():
    key, sep, ref = line.partition("=")
    if line.startswith("#") or not sep or not ref.startswith("op://"):
        out.append(line)
        continue
    read = subprocess.run(["op", "read", "--no-newline", ref], capture_output=True, text=True)
    if read.returncode:
        sys.exit(f"build-env: cannot read {ref}: {read.stderr.strip()}")
    out.append(f"{key}={quote(read.stdout)}")
sys.stdout.write("\n".join(out) + "\n")
