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
  gutter). Pi-hole's summary cards carry a faint wash of Pi-hole's own colours. Beszel's
  server widget is one item holding every machine: its own card is clear and each machine
  gets the panel glass and blue hover, so they read as separate cards. Thin white
  Open Sans; blue `#2d8cf0`, green `#4cd964`. `glazzed.css`.
- **bluematrix**: the Ghostty terminal's Blue Matrix palette (`#101116`, `#00b0ff`, `#00ff9c`),
  rounded glass cards over a faint grid, JetBrains Mono headings. `bluematrix.css`.

- `layout.py`: the whole layout. A top row (clock, weather, Uptime Kuma, Pi-hole), then headed
  groups that never collapse (Homarr "dynamic" sections). First every link, one balanced row
  per group: Apps, Monitoring & network, Infrastructure. Then the live panels: Servers (Beszel,
  one card per machine), Host history (Beszel charts for prx1 and prx2, 24 hours), Containers &
  updates (containers on all three hosts and a Releases list of everything homelab-apps pins),
  Documents & notes. Releases uses Docker Hub where a project publishes there; only Homarr and
  Arcane come from GitHub, as anonymous GitHub allows 60 requests an hour. It imports `homarr_session.py`, which signs in with the Homarr login
  copied from 1Password (`Homelab - Homarr`, vault **Development**) to `~/.homarr-setup/login.json` on prdsrv1;
  delete that file afterwards. The host history charts name their machines by Beszel system
  id (`HOST_HISTORY`), which changes if the Beszel hub is rebuilt from nothing.

The Beszel integration (Management > Integrations) is not made by `build-board.py`: it was
added by hand with Beszel's read-only `homarr` user (its password is in 1Password, vault
Development). On a Homarr rebuilt from nothing, add it
again, named `Beszel`, before running `layout.py`.

Homarr 2 (2026-10-03): gridstack is gone, so widget cards are `.board-grid-item-content` and dynamic
sections became containers (they keep `hl-group`). 2.0.0 also sizes the Beszel history charts from
the card height times the board zoom (1.49 at 1728px), so they overflowed; `glazzed.css` lays them
out with flex instead (rows share the card, two columns from a 380px card, room on the left for
the axis numbers). Checked with headless Chrome at 430 to 2560px: every chart inside its card.

Homarr quirk: a category is open when its per-user `collapsed` value is `true` (the component
treats it as "opened"), so `section.changeCollapsed` with `collapsed: true` expands it.
Screenshots were taken with headless Chrome (puppeteer-core) using a session cookie.
