import json, ssl, urllib.request, urllib.parse, http.cookiejar, os
BASE = "https://dash.example.com"
SETUP = os.path.expanduser("~/.homarr-setup")
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), urllib.request.HTTPSHandler(context=ssl.create_default_context()))

def login():
    creds = json.load(open(f"{SETUP}/login.json"))
    csrf = json.load(opener.open(BASE + "/api/auth/csrf"))["csrfToken"]
    data = urllib.parse.urlencode({"csrfToken": csrf, "name": creds["name"], "password": creds["password"], "json": "true", "callbackUrl": BASE}).encode()
    opener.open(urllib.request.Request(BASE + "/api/auth/callback/credentials", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}))
    if not any("session-token" in c.name for c in jar):
        raise SystemExit("login failed")

def query(proc, inp=None):
    url = BASE + "/api/trpc/" + proc + ("?input=" + urllib.parse.quote(json.dumps({"json": inp})) if inp is not None else "")
    return json.load(opener.open(url))["result"]["data"]["json"]

def mutate(proc, inp):
    req = urllib.request.Request(BASE + "/api/trpc/" + proc, data=json.dumps({"json": inp}).encode(), headers={"Content-Type": "application/json"})
    try:
        return json.load(opener.open(req))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{proc}: HTTP {e.code} {e.read().decode()[:400]}")
