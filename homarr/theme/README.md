# Homarr theme and layout

Two looks; `apply_theme.py <name>` switches between them. Since Homarr 2 it sets the instance
branding, so the look covers every page including sign-in: name "Homelab", the `>_` logo
(`logo.svg`, uploaded once to Homarr's media store as `homelab-logo.svg`) as logo and favicon,
colours, corner style, and the theme as global CSS. The board keeps opacity and radius and no
CSS of its own, so the theme lives in one place. Run it on the Mac (Touch ID once):

- **glazzed** (current, from 2026-09-30): after the Glazzed admin theme, with subtle rounded
  corners (panels 8 px, section frames 10 px, inner boxes 6 px, buttons and badges 4-5 px).
  A blurred mesh of slate blue, violet, crimson and teal; translucent glass with hairline
  borders; three glass levels (panel, inset, group) so no widget keeps its own grey (Uptime
  Kuma's stat tiles, Pi-hole's cards, node lists, table header, buttons).
  Sections draw no frame: every item stands on its own like the top row, under a plain light
  header in the gap above (never overlapping); per-widget title badges are hidden. Section
  cards line up with the top row's columns (the section's inner grid is pulled out by one
  gutter). Pi-hole's summary cards carry a faint wash of Pi-hole's own colours. Beszel's
  server widget is one item holding every machine: its own card is clear and each machine
  gets the panel glass and blue hover, so they read as separate cards. Thin white
  Open Sans; blue `#2d8cf0`, green `#4cd964`. `glazzed.css`.
- **bluematrix**: the Ghostty terminal's Blue Matrix palette (`#101116`, `#00b0ff`, `#00ff9c`),
  rounded glass cards over a faint grid, JetBrains Mono headings. `bluematrix.css`.

- `../apps.toml`: every app tile, by group and in order (name, link, icon, status check,
  description). Add or change a tile there, then `python3 layout.py` (`--dry-run` first): it
  creates or updates the apps in Homarr and places the tiles. Compose labels were considered and
  dropped: Homarr reads them only during first-time setup, most tiles are not containers, and
  the two Pi-holes share one compose file.
- `../widgets/*.json` + `widgets.py`: custom widgets (Homarr 2 Custom JSX). `widgets.py` previews
  each one, runs every query against the real service (Homarr's required evidence) and saves it;
  `layout.py` places it (WIDGETS). Sources name saved integrations, so the files hold no ids or
  secrets. **Backups & jobs** (under Servers, two rows high; eight boxes, four a row on the top row's columns, one a row on a phone; icon and status colour per job, name, schedule, last run; narrower screens show the time in place of the schedule): the last Proxmox backup of
  each machine from the task log (Homarr's Proxmox user is read-only, which cannot list backup
  files, but can read tasks), and the last heartbeat of the dump, off-site and property-search
  push monitors from Uptime Kuma's homelab status page. It shows times and OK/Failed; Homarr gives
  templates no clock, so it cannot flag a backup as overdue by itself.
- No sidebar: a right "rail" (Homarr 2) with a server table was tried on 2026-10-03 and dropped;
  Base is 12 columns. The owner's header adds a Docker button (apply_theme.py). The Statistics
  widget is not used: it shows hand-refreshed snapshots, and the live widgets do better.
- Grid and alignment: 12 columns (24 was tried: Homarr zooms a 24-column board to a third and
  widgets that do not compensate became unreadable). Every row is a container, the top row too
  ("Overview", no heading), so all cards share one inner grid and their edges line up. Backups &
  jobs is a tile row: six boxes on the tiles' columns. On Mobile containers are as tall as their
  contents (MOBILE_MIN for Servers) and in the desktop order.
- Text: the board is drawn zoomed out (about two-thirds); widgets that do not scale their text back
  (app names, Uptime Kuma) and section headings get sizes multiplied by
  `--board-canvas-inverse-scale` in glazzed.css; badges use Mantine's `--mantine-scale`.
- Homarr keeps at most 16384 characters of custom CSS; `apply_theme.py` uploads the theme without
  comments and spare whitespace (glazzed.css: about 11,000), so the comments stay in the files.
- `deploy.py` runs apply_theme.py, widgets.py and layout.py in one process: one Touch ID prompt.
- `layout.py`: the whole layout (Homarr 2: containers, Base and Mobile layouts; it sets Base and
  keeps Mobile's own positions; widget settings are defaults for new widgets only). A top row (clock, weather, Uptime Kuma, Pi-hole), then headed
  groups that never collapse (Homarr "dynamic" sections). First every link, one balanced row
  per group: Apps, Monitoring & network, Infrastructure. Then the live panels: Servers (Beszel,
  one card per machine), Host history (Beszel charts for prx1 and prx2, 24 hours), Containers &
  updates (containers on all three hosts and a Releases list of what homelab-apps pins: upstream's
  latest release only, checked every 6 hours, never the running version; `../../check-updates.sh`
  compares; SQL Server, Oracle and property-search are not listable),
  Notes (the notebook, full width; its text is `../widgets/notes.html`, set by `layout.py --notes`;
  the Paperless widget was dropped on 2026-10-29: Paperless holds no documents, so it only showed
  zeros). Releases uses Docker Hub where a project publishes there; only Homarr and
  Arcane come from GitHub, as anonymous GitHub allows 60 requests an hour. It imports `homarr_session.py`, which reads the Homarr API key from
  1Password (`homelab-homarr-api`, vault **Development**; Touch ID once) and sends it as the `ApiKey`
  header, so no password or key file is needed. Run the scripts on the Mac from this folder. The host history charts name their machines by Beszel system
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
