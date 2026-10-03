"""Talk to Homarr's API as an administrator, for apply_theme.py and layout.py (run on the Mac).

The API key comes from 1Password (`homelab-homarr-api`, vault Development; one Touch ID prompt)
and goes in the `ApiKey` header; nothing is written to disk. Homarr keeps only a hash of each
key, so it is shown once: to replace it, create one under Management > Tools > API, paste it
into that item, and delete the old key in Homarr.
"""
import json
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://dash.example.com"
KEY_REF = "op://Development/homelab-homarr-api/credential"
_headers = {}
opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context()))


def api_key():
    read = subprocess.run(["op", "read", KEY_REF], capture_output=True, text=True)
    if read.returncode or not read.stdout.strip():
        raise SystemExit(f"Homarr API key not readable from 1Password ({KEY_REF}): {read.stderr.strip()}")
    return read.stdout.strip()


def login():
    """Load the API key and check Homarr accepts it (named for when this signed in with a password)."""
    _headers["ApiKey"] = api_key()
    try:
        opener.open(urllib.request.Request(BASE + "/api/apps", headers=_headers))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Homarr refused the API key (HTTP {e.code}); is {KEY_REF} current?")


def query(proc, inp=None):
    url = BASE + "/api/trpc/" + proc + ("?input=" + urllib.parse.quote(json.dumps({"json": inp})) if inp is not None else "")
    return json.load(opener.open(urllib.request.Request(url, headers=_headers)))["result"]["data"]["json"]


def mutate(proc, inp):
    req = urllib.request.Request(BASE + "/api/trpc/" + proc, data=json.dumps({"json": inp}).encode(),
                                 headers={**_headers, "Content-Type": "application/json"})
    try:
        return json.load(opener.open(req))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{proc}: HTTP {e.code} {e.read().decode()[:400]}")


def upload(name, content, content_type):
    """Upload one file to Homarr's media store; returns its id (served at /api/user-medias/<id>)."""
    boundary = "----homelab" + "".join(f"{b:02x}" for b in __import__("os").urandom(8))
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{name}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/trpc/media.uploadMedia", data=body,
                                 headers={**_headers, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        return json.load(opener.open(req))["result"]["data"]["json"][0]
    except urllib.error.HTTPError as e:
        raise SystemExit(f"upload {name}: HTTP {e.code} {e.read().decode()[:400]}")
