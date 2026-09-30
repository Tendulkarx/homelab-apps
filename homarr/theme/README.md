# Homarr theme and layout

The Homelab board's look, in the Blue Matrix palette of the Ghostty terminal (background
`#101116`, blue `#00b0ff`, green `#00ff9c`): glass cards over a dark gradient with a faint grid,
JetBrains Mono headings, and a `>_` logo (`logo.svg`, set as a data URI for logo and favicon).

- `dashboard.css`: the board's custom CSS (Homarr: board settings → Appearance → Custom CSS).
- `layout.py`: the whole layout. A top row (clock, weather, Uptime Kuma, Pi-hole), then headed
  groups that never collapse (Homarr "dynamic" sections): Apps, Monitoring & network, Servers
  (one Proxmox panel per host), Containers & docs. Every service is a compact app tile. Also
  applies the CSS and logo. It imports `homarr_session.py`, which signs in with the Homarr login
  copied from 1Password (`Homelab - Homarr`) to `~/.homarr-setup/login.json` on prdsrv1;
  delete that file afterwards.

Homarr quirk: a category is open when its per-user `collapsed` value is `true` (the component
treats it as "opened"), so `section.changeCollapsed` with `collapsed: true` expands it.
Screenshots were taken with headless Chrome (puppeteer-core) using a session cookie.
