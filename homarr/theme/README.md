# Homarr theme and layout

Two looks for the Homelab board; `apply_theme.py <name>` switches between them (CSS, colours,
opacity, corner radius, `>_` logo from `logo.svg` as logo and favicon):

- **glazzed** (current, from 2026-09-30): after the Glazzed admin theme, with subtle rounded
  corners (panels 8 px, section frames 10 px, inner boxes 6 px, buttons and badges 4-5 px).
  A blurred mesh of slate blue, violet, crimson and teal; translucent glass with hairline
  borders; three glass levels (panel, inset, group) so no widget keeps its own grey (Uptime
  Kuma's and Paperless's stat tiles, Pi-hole's cards, node lists, table header, buttons).
  Sections draw no frame: every item stands on its own like the top row, under a plain light
  header in the gap above (never overlapping); per-widget title badges are hidden. Section
  cards line up with the top row's columns (the section's inner grid is pulled out by one
  gutter). Pi-hole's summary cards carry a faint wash of Pi-hole's own colours. Thin white
  Open Sans; blue `#2d8cf0`, green `#4cd964`. `glazzed.css`.
- **bluematrix**: the Ghostty terminal's Blue Matrix palette (`#101116`, `#00b0ff`, `#00ff9c`),
  rounded glass cards over a faint grid, JetBrains Mono headings. `bluematrix.css`.

- `layout.py`: the whole layout. A top row (clock, weather, Uptime Kuma, Pi-hole), then headed
  groups that never collapse (Homarr "dynamic" sections). First every link, one balanced row
  per group: Apps, Monitoring & network, Servers & backups. Then the live panels: Proxmox hosts
  (one panel per host, no Nodes list), Containers & updates (containers on all three hosts and
  a Releases list of everything homelab-apps pins), Documents & notes. Releases uses Docker Hub
  where a project publishes there, as anonymous GitHub allows only 60 requests an hour. It imports `homarr_session.py`, which signs in with the Homarr login
  copied from 1Password (`Homelab - Homarr`) to `~/.homarr-setup/login.json` on prdsrv1;
  delete that file afterwards.

Homarr quirk: a category is open when its per-user `collapsed` value is `true` (the component
treats it as "opened"), so `section.changeCollapsed` with `collapsed: true` expands it.
Screenshots were taken with headless Chrome (puppeteer-core) using a session cookie.
