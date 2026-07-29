# SolarOps AI — Monitoring (Phase 7c, folded into the full stack in Phase 8)

Prometheus + Grafana over the metrics the API already exposes at `/metrics`.
Docker is only needed to *view* the dashboards — the metrics themselves work
with no Docker at all (see below).

There are now two ways to get here, for two different setups:

- **API on the host, Prometheus/Grafana in Docker** (Phase 7c, below) — for
  when you're running the API via `python scripts/run_api.py` and just want
  the dashboards.
- **Everything in Docker** (Phase 8) — `docker compose --profile monitoring
  up` from the repo root brings up the full stack (api/redis/postgres/mlflow)
  plus Prometheus/Grafana scraping the containerized `api` service directly
  by its compose service name, via `monitoring/prometheus/prometheus.docker.yml`
  (`docker-compose.yml`'s `prometheus`/`grafana` services). Same dashboards,
  same URLs — see `DEPLOYMENT.md` for the full run command.

## Without Docker

Start the API (`python scripts/run_api.py`), then:

```
curl http://127.0.0.1:8000/metrics
```

This is real Prometheus exposition format — every counter/histogram/gauge
listed in the Phase 7c report, live. That's enough to confirm instrumentation
is working without touching Docker.

## With Docker — the dashboards (API still running on the host)

1. Start the API on the host first (`python scripts/run_api.py`) — Prometheus
   scrapes it from inside its container, so it needs to already be running.
2. From the repo root:
   ```
   docker compose -f docker-compose.monitoring.yml up
   ```
   (This is a separate compose file from the existing `docker-compose.yml`,
   which is just Redis for integration tests — run either independently, or
   both together with `docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up`.)
3. **Prometheus**: http://localhost:9090 — Status → Targets should show
   `solarops-api` as `UP`. If it's down, the API on the host probably isn't
   running yet, or something else is already bound to port 8000.
4. **Grafana**: http://localhost:3000 — log in with `admin` / `admin` (change
   it if you leave this running anywhere reachable). Both dashboards are
   provisioned automatically under the **SolarOps** folder — no manual setup.

## Dashboards

- **Operations** — commands issued / blocked by safety / rejected (by
  reason), approvals required, approval wait time (p50/p95), execution
  latency (p50/p95), overall success rate, and API request volume by route.
  This is the "is the pipeline healthy" view.
- **AI & Safety** — recommendation latency, forecasts produced by kind,
  anomalies detected by type and severity, commands blocked by safety,
  verification failures, and which model/detector versions are currently
  registered. This is the "is the reasoning trustworthy" view.

Generate some data to watch move: open the dashboard, then in another
terminal/tab drive the pipeline — e.g. `POST /sites/site-001/decision-cycle`
a few times via `/docs`, or click through the dashboard app's Recommendations
→ Approvals flow. Both dashboards refresh every 5 seconds.

## Platform note

`docker-compose.monitoring.yml` adds `extra_hosts:
host.docker.internal:host-gateway` to the Prometheus service so the scrape
target resolves correctly on Linux too, not just Docker Desktop (Windows/Mac)
— nothing extra to configure either way.

## Known gap, honestly

`solarops_commands_auto_rejected_by_confidence_total` always reads 0. Phase
6d's confidence rule (Document 9 §8) only ever *escalates* an
otherwise-auto-executable command to human approval — there's no code path
where low confidence alone causes an auto-*rejection*. The metric is
declared (so a dashboard panel for it doesn't 404) rather than removed or
faked; see the `TODO(6d-confidence-auto-reject)` comment in
`src/solarops/observability/metrics.py`.
