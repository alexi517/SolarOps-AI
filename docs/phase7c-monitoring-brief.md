# Phase 7c Brief — Monitoring (the last build)

**For:** Claude Code (or manual execution)
**Scope:** Operational monitoring only — metrics + dashboards. This completes the
platform.
**Source of truth:** CESF (Doc 7) §17, Document 6 §11, the LangGraph doc §11.

**IMPORTANT — save this file to `docs/phase7c-monitoring-brief.md` before building.**

## 0. What this is
Everything works; this makes it *observable like a production system*. It exposes
the operational numbers the architecture asks to track, in the standard format
monitoring tools read, and provides ready-made dashboards to view them. No new
business logic — this is instrumentation over the system that already exists.

## 1. Metrics to expose (from CESF §17, Doc 6 §11)
Expose these as Prometheus metrics. Where a value isn't cheaply available yet,
add the metric and leave it at zero/unpopulated with a `TODO`, rather than
faking it.

**Command pipeline (CESF §17):**
- commands issued (counter)
- commands blocked by safety (counter)
- commands rejected by policy (counter)
- commands auto-rejected by risk / by low confidence (counters)
- approvals required / approved / rejected (counters), and approval wait time
  (histogram)
- execution latency (histogram)
- retry count (counter)
- command success / failure by category (counters)
- verification failures (counter)

**AI / model (Doc 6 §11):**
- recommendation latency (histogram)
- forecasts produced by kind (counter)
- anomalies detected by type/severity (counter)
- registered model versions (gauge/info)

**API / ops (Doc 6 §11):**
- API request count + latency by route (histogram)
- telemetry updates processed (counter)

## 2. How to expose it
- Use `prometheus-client`. Instrument the existing application services /
  pipeline at the points where these events already happen (emit a metric where a
  domain event is already emitted — reuse those seams; don't scatter counters
  arbitrarily).
- The existing `GET /metrics` endpoint (stubbed in 7a) now returns the real
  Prometheus exposition format. Prefer wiring metrics via the domain events the
  pipeline already emits, so instrumentation stays at the edge/application layer
  and the domain stays clean.
- Add `prometheus-client` to `pyproject.toml`.

## 3. Grafana + Prometheus (Docker Compose)
- Add a `docker-compose.monitoring.yml` (or extend the planned compose file) with
  a **Prometheus** service (scraping the API's `/metrics`) and a **Grafana**
  service.
- Provide a Prometheus scrape config pointing at the API.
- Provide **pre-built Grafana dashboards as provisioned JSON** (checked into the
  repo under `monitoring/grafana/`), so the dashboards exist on first run rather
  than needing manual clicking. At least two dashboards:
  - **Operations** — commands issued/blocked/completed, approval wait time,
    execution latency, success rate.
  - **AI & safety** — recommendations, forecasts, anomalies by severity,
    commands blocked by safety, verification failures.
- A short `monitoring/README.md`: how to start it
  (`docker compose -f docker-compose.monitoring.yml up`), the Grafana URL/login,
  and which dashboard shows what.

## 4. Honesty & scope
- Instrumentation only — no business logic changes; existing behaviour and tests
  unchanged.
- Metrics that can't be populated cheaply yet are declared but left at zero with a
  clear `TODO`, never faked.
- Docker is only required to *view* Grafana; the `/metrics` endpoint itself works
  without Docker (can be curled directly), so tests don't depend on containers.

## 5. Definition of done (7c)
- `GET /metrics` returns real Prometheus-format metrics covering the CESF §17 /
  Doc 6 §11 list (populated where available, TODO-zero where not).
- `docker compose -f docker-compose.monitoring.yml up` brings up Prometheus +
  Grafana with the two dashboards provisioned and reading live data from a running
  API.
- A test confirms `/metrics` returns valid Prometheus output and that at least the
  command-pipeline counters move when a command runs.
- `pytest`, `ruff`, `lint-imports` green.
- **Report:** files created, the metrics now exposed, how to view the Grafana
  dashboards, and test results. This completes Phase 7 and the build.