# Phase 7b — Dashboard Polish Pass (Streamlit)

**For:** Claude Code
**Scope:** Presentation only. Do **not** change the thin-client structure, the
`api_client.py` routing, or any logic. `grep -rn "solarops" dashboard/` must stay
zero. Re-run `pytest` and `ruff check dashboard tests/dashboard` and keep them
green.

**Goal:** Restyle the existing working dashboard to evoke a clean solar-energy
app — the *spirit* of a modern energy dashboard (soft green palette, big numbers,
circular gauges, gentle area charts, rounded cards), rendered as a polished web
dashboard. This is Streamlit, not a bespoke mobile app — match the feel, not a
pixel copy.

## 1. Theme (`.streamlit/config.toml`)
A clean, light, energy-forward palette (reference has a soft white/green feel):
- `base = "light"`
- `primaryColor = "#4CAF50"` (fresh energy green — accent for buttons/highlights)
- `backgroundColor = "#F7FAF7"` (very soft off-white green tint)
- `secondaryBackgroundColor = "#FFFFFF"` (cards sit on white)
- `textColor = "#1C2B24"` (deep slate-green, high contrast)
- a clean sans font (`font = "sans serif"`)
Also offer a commented-out **dark** variant in the file (charcoal base `#12160F`,
same green accent) so the user can flip to dark by swapping the block.

## 2. Global CSS (one module, e.g. `dashboard/style.py`)
Centralise all custom CSS in one string injected once via
`st.markdown(..., unsafe_allow_html=True)`. Include:
- **Rounded card containers** — a `.card` class: white background, ~16px radius,
  soft shadow (`box-shadow: 0 2px 12px rgba(0,0,0,0.06)`), ~20px padding.
- **Status pills** — `.pill-green` / `.pill-amber` / `.pill-red`: small rounded
  badges with soft background tint and darker text.
- Tighten default Streamlit padding; hide the default menu/footer for a cleaner
  look; round buttons; give the sidebar a subtle tint.
- A subtle green gradient header strip at the top of each page.

## 3. Layout & components (every page)
- `st.set_page_config(layout="wide", page_title="SolarOps", page_icon="⚡")`.
- Each page opens with a header row: page title (left), site selector + a
  "last updated HH:MM" caption (right).
- **Overview** — a row of `st.metric` cards for the headline numbers (Battery SOC,
  Solar Power, Building Load, Grid status), each wrapped in a `.card`. Below, two
  charts side by side (section 4). Any fault/grid-outage shown as a red pill banner
  at the top.
- **Approvals** — each pending command in its own `.card`: risk level as a
  prominent pill (HIGH = amber/red), the recommendation rationale readable, and a
  button row — **Approve** (`type="primary"`, green) and **Reject** (styled red).
  Success/error shown as a toast (`st.toast`) plus an inline confirmation.
- Consistent use of `.card` wrappers everywhere so the whole app reads as tidy
  panels on a soft background, not raw stacked widgets.

## 4. Charts (Plotly, themed)
Replace default charts with themed Plotly figures (transparent background,
green palette, no gridline clutter, rounded fonts):
- **Battery SOC gauge** — a Plotly `Indicator` gauge (0–100%), green fill,
  amber/red zones near the limits — echoes the circular gauges in the reference.
- **Solar vs Load** — an area/line chart with a soft green fill under solar and a
  contrasting line for load (the reference's signature soft-green area look).
- **Forecasts page** — plot the registered solar forecast the same way; show the
  unavailable load/battery forecasts as tidy placeholder `.card`s reading
  "Not yet available" with the API's own reason text — designed, not blank.
- Set `config={"displayModeBar": False}` so charts look clean.

## 5. Honesty & rules (unchanged)
- Still a thin viewer: no `solarops` imports, all data via `api_client.py`.
- Never fabricate data; unavailable = a tidy placeholder card, not fake numbers.
- API key / base URL still from env/config.

## 6. Definition of done
- The dashboard looks like a designed energy dashboard: soft green theme, rounded
  cards, metric tiles, a battery gauge, a soft-green solar/load chart, coloured
  status pills, a polished Approvals console.
- Structure unchanged; `grep -rn "solarops" dashboard/` still zero.
- `pytest` and `ruff check dashboard tests/dashboard` still green.
- Report what changed (files touched, components added) and confirm the thin-client
  rule and tests still hold.