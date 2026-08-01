# SolarOps AI — React dashboard (mobile-first)

A second operator UI, built with React + Vite instead of Streamlit, for a
mobile-first look Streamlit's own rendering model can't produce (rounded
cards, a self-powered ring, an animated energy-flow diagram). This runs
**alongside** `dashboard/` (the Streamlit UI), not instead of it — both talk
to the same FastAPI backend over plain HTTP, nothing shared between them.

**Not verified end-to-end yet.** Node.js wasn't available in the environment
this was built in, so `npm install`/`npm run dev` were never actually run
here. Everything was written carefully against the real API schemas, but you
are the first to actually run it — if something's off, it's most likely a
small one, not an architectural one.

## Setup

```bash
cd dashboard-react
npm install
cp .env.example .env   # edit if your API isn't on the default port
npm run dev
```

Opens on `http://localhost:5173` by default.

## Before it'll work: two things on the API side

1. **The API must be running**: `python scripts/run_api.py` from the repo root
   (or your deployed API's URL, set via `VITE_API_BASE_URL`).
2. **CORS**: the API now has `CORSMiddleware` configured
   (`src/solarops/api/app.py`), allowing `http://localhost:5173` and
   `http://127.0.0.1:5173` by default (`SOLAROPS_CORS_ALLOWED_ORIGINS` env var
   to change this — comma-separated). If you deploy this frontend somewhere
   else (Vercel, Netlify, etc.), add that origin to the API's env var or the
   browser will silently block every request.

## What's here

- `src/api.js` — fetch wrapper over the same endpoints `dashboard/api_client.py`
  uses (state, forecasts, recommendations, approvals, decision-cycle).
- `src/App.jsx` — polls `GET /state` every 15s (read-only, doesn't advance the
  simulation), builds a session-only history for the sparkline, and has a
  "Run decision cycle" button that calls `POST /decision-cycle` (this is the
  only thing that actually advances the Digital Twin — same as the Streamlit
  dashboard, the API itself has no auto-polling).
- `src/components/` — one file per visual piece: the self-powered ring, the
  energy-flow diagram (solar/battery/grid vs. home, direction and animation
  driven by the real sign conventions in `DigitalTwin.tick()`), the session
  sparkline (hand-rolled SVG, no charting library dependency), the system
  overview list, status pills, and pending approvals with inline approve/reject.

## Honest limitations

- **The sparkline only shows this browser tab's session**, not real history —
  the API has no historical-state endpoint yet (`docs/CODE-WALKTHROUGH.md`
  notes this as a known gap, "Layer 2" in the original design docs). Refresh
  the page and the chart starts over.
- Only the **Overview**-equivalent screen exists so far (plus an approvals
  card). Forecasts/anomalies/commands screens from the Streamlit dashboard
  don't have React equivalents yet — same pattern (`api.js` already has the
  fetch functions for forecasts/anomalies/commands) would extend this.
- No test suite yet — `dashboard/` has `tests/dashboard/` using Streamlit's
  `AppTest`; this would need its own (e.g. Vitest + React Testing Library).

## Build for deployment

```bash
npm run build
```

Outputs static files to `dist/` — deployable to Vercel, Netlify, GitHub Pages,
or any static host. Set `VITE_API_BASE_URL` for that host's build-time env,
since Vite bakes `VITE_*` vars in at build time, not runtime.
