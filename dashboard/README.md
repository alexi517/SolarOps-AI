# SolarOps AI — Dashboard

A thin Streamlit viewer over the Phase 7a API. It holds no business logic and
imports nothing from `solarops` — every screen is just an HTTP call to the
API and a rendering of what comes back. Swap it for React tomorrow and
nothing on the API side changes.

## Run it

Install the extra (from the repo root):

```
pip install -e ".[dashboard]"
```

1. Start the API first (from the repo root):

   ```
   python scripts/run_api.py
   ```

   It listens on `http://127.0.0.1:8000` by default.

2. Start the dashboard (from the repo root):

   ```
   streamlit run dashboard/app.py
   ```

   It opens in your browser, pointed at `http://127.0.0.1:8000` by default.

## Configuration

Set these environment variables before launching if you need something other
than the defaults (`dashboard/config.py`):

| Variable | Default | Purpose |
|---|---|---|
| `SOLAROPS_API_BASE_URL` | `http://127.0.0.1:8000` | Where the API is running |
| `SOLAROPS_API_KEY` | `solarops-demo-key` | Sent as `X-API-Key` on the approval POSTs |
| `SOLAROPS_SITE_ID` | `site-001` | The site the dashboard displays |
| `SOLAROPS_API_TIMEOUT_SECONDS` | `10` | HTTP request timeout |

The API key must match whatever the API is actually enforcing
(`SOLAROPS_API_KEY` on the API side too) — they're independent processes, so
if you override one, override the other the same way.

## Demo click-path

1. Open the **Recommendations** screen and click **Run decision cycle now**.
   With the default site config this reliably produces a `CHARGE_BATTERY`
   recommendation classified `HIGH` risk, so the resulting command pauses
   awaiting approval rather than executing immediately.
2. Open **Approvals** — the paused command is listed, with its risk level,
   the action it wants to take, and its current params.
3. Click **Approve** (or try **Reject**, or edit the params JSON and use
   **Modify & approve**). The screen calls the API with the configured
   `X-API-Key`, then shows the resulting command — watch its status move to
   `COMPLETED` (or `REJECTED_BY_OPERATOR` if you rejected it), verification
   result included.
4. Open **Commands** to see it in the full history, select it, and read the
   complete immutable audit trail of everything that happened to it.
5. Open **Overview** and **Forecasts** any time to see the current state and
   what's actually predictable right now — Forecasts is deliberately honest
   that only solar is registered; load and battery-SOC show as
   "not yet available" rather than a faked chart.
