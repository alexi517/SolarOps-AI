# Phase 7b Brief — The Dashboard (Streamlit)

**For:** Claude Code (or manual execution)
**Scope:** The operator dashboard only. Monitoring (7c) follows.
**Prerequisite:** Phase 7a (the API) is built and runnable.

**IMPORTANT — save this file to `docs/phase7b-dashboard-brief.md` before building.**

## 0. What this is (and is not)
A **thin viewer** that calls the Phase 7a API over HTTP and displays the results.
It contains **no business logic, no direct access to the domain, no database, no
imports from `solarops`** — it only makes HTTP requests to the API and renders the
JSON that comes back. This separation is the point: all intelligence stays behind
the API; the dashboard is a face over it. (In an interview: "the dashboard is a
thin client over the API — swap it for React tomorrow and nothing else changes.")

## 1. Where it lives
A **new top-level `dashboard/` folder**, separate from `src/solarops/`. It is its
own small program, run with `streamlit run dashboard/app.py`, that talks to the
API base URL (configurable, default `http://127.0.0.1:8000`).

```
dashboard/
├── app.py              # entry point / navigation
├── api_client.py       # thin wrapper over httpx calls to the API (one place)
├── pages/
│   ├── overview.py     # current site state
│   ├── forecasts.py
│   ├── anomalies.py
│   ├── recommendations.py
│   ├── approvals.py    # the human-in-the-loop screen
│   └── commands.py     # command history + audit trail
└── config.py           # API base URL, API key (from env, not hardcoded)
```

- Add `streamlit` to the dev/dashboard dependencies in `pyproject.toml`.
- **No import-linter change and no new `solarops` dependency** — the dashboard is
  outside the package and must stay that way. If it ever imports `solarops`, that's
  a mistake.

## 2. The screens
Each screen calls one or more API endpoints and displays the result clearly.

- **Overview** — `GET /sites/{id}/state`: current battery SOC, solar/load/grid
  power, temperatures, grid status. Show the headline numbers big; flag anything
  abnormal (e.g. grid not connected, any fault).
- **Forecasts** — `GET /sites/{id}/forecasts`: plot what's available. **Show
  honestly** that only solar is registered; load and battery-SOC display as
  "not yet available" rather than blank or faked.
- **Anomalies** — `GET /sites/{id}/anomalies`: list detected anomalies with their
  six fields (type, severity, confidence, affected asset, evidence, recommended
  action). Colour by severity.
- **Recommendations** — `GET /sites/{id}/recommendations`, and a button that calls
  `POST /sites/{id}/decision-cycle` to run a fresh reasoning cycle. Show each
  recommendation's rationale: why, why now, evidence, alternatives, risks.
- **Approvals (the key screen)** — `GET /sites/{id}/approvals/pending`: list
  commands paused awaiting a human, each with **Approve / Reject / Modify**
  buttons that call the corresponding API POSTs (sending the API key). After the
  action, refresh and show the command's new state. This is the human-in-the-loop
  workflow made visible and clickable.
- **Commands** — `GET /sites/{id}/commands` and `GET /commands/{id}/audit`: the
  command history with status, and the full immutable audit trail for a selected
  command.

## 3. Behaviour & UX rules
- All API calls go through the single `api_client.py` (one place to set base URL,
  API key, timeouts, and error handling) — don't scatter `httpx` calls across pages.
- Handle the API being down gracefully: show "cannot reach API" instead of a stack
  trace.
- Never fabricate data. If an endpoint returns "unavailable" (e.g. load forecast),
  the screen says so plainly.
- The API key comes from an environment variable / `config.py`, never hardcoded in
  a page.

## 4. Definition of done (7b)
- `streamlit run dashboard/app.py` launches a working multi-page dashboard against
  a running API.
- All six screens display real data from the API.
- The Approvals screen can approve/reject a paused command end to end and show the
  resulting state change — the same workflow proven via the API in 7a, now
  clickable by a human.
- The dashboard imports nothing from `solarops` and holds no business logic.
- A short `dashboard/README.md`: how to run it (start the API, then
  `streamlit run dashboard/app.py`), and the demo click-path (run a decision cycle
  → see it pending → approve it → watch it complete).
- **Report:** files created, the screens built, a plain-English walkthrough of
  approving a command from the dashboard, and confirmation the dashboard has no
  `solarops` imports. Stop before 7c.