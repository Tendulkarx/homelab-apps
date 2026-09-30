# Homarr theme and layout

Two looks for the Homelab board; `apply_theme.py <name>` switches between them (CSS, colours,
opacity, corner radius, `>_` logo from `logo.svg` as logo and favicon):

- **glazzed** (current, from 2026-09-30): after the Glazzed admin theme. A blurred mesh of slate
  blue, violet, crimson and teal; square translucent glass panels with hairline borders; group
  titles as header strips, widget titles in the top right; thin white Open Sans; blue `#2d8cf0`,
  green `#4cd964`. `glazzed.css`.
- **bluematrix**: the Ghostty terminal's Blue Matrix palette (`#101116`, `#00b0ff`, `#00ff9c`),
  rounded glass cards over a faint grid, JetBrains Mono headings. `bluematrix.css`.

- `layout.py`: the whole layout. A top row (clock, weather, Uptime Kuma, Pi-hole), then headed
  groups that never collapse (Homarr "dynamic" sections): Apps, Monitoring & network, Servers
  (one Proxmox panel per host), Containers & docs. Every service is a compact app tile. Also
  applies the CSS and logo. It imports `homarr_session.py`, which signs in with the Homarr login
  copied from 1Password (`Homelab - Homarr`) to `~/.homarr-setup/login.json` on prdsrv1;
  delete that file afterwards.

Homarr quirk: a category is open when its per-user `collapsed` value is `true` (the component
treats it as "opened"), so `section.changeCollapsed` with `collapsed: true` expands it.
Screenshots were taken with headless Chrome (puppeteer-core) using a session cookie.
