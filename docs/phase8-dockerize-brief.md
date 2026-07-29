# Phase 8 Brief — Dockerize the Platform (run it for real)

**For:** Claude Code (or manual execution)
**Scope:** Package the whole system so it runs with a single command, wired to
real infrastructure (Redis, Postgres, MLflow) instead of in-memory fakes — plus
the existing monitoring. No new product features.

**IMPORTANT — save this file to `docs/phase8-dockerize-brief.md` before building.**

## 0. Goal
`docker compose up` brings up the entire platform — the API, its real
dependencies, and monitoring — all wired together, on any machine with Docker,
with no manual `.venv` steps. This is the "wire it for real" pass.

## 1. Expect real-infrastructure friction (read first)
Until now Redis/Postgres/MLflow have been faked with in-memory adapters and
`fakeredis`/SQLite. Connecting the *real* services will surface gaps: connection
config, startup ordering, data that didn't need to persist before, MLflow needing
a real backend/artifact store. **Surface these plainly and fix them one at a
time** — do not paper over a real integration problem to make the container start.
If a required behaviour genuinely isn't ready for a real backing service, flag it
and leave a marked seam rather than a silent fake.

## 2. Application container
- Add a `Dockerfile` for the app:
  - Base on an official slim Python 3.12 image.
  - Install the project (`pip install .` — production deps; ML libs are heavy, so
    keep the image lean and use layer caching for dependencies).
  - Run the API with `uvicorn` (production settings, not `--reload`).
  - Use a non-root user; expose the API port.
- Add a `.dockerignore` (exclude `.venv`, caches, `.git`, tests artifacts, etc.).

## 3. Real backing services (compose)
Create a top-level `docker-compose.yml` that brings up:
- **api** — built from the Dockerfile above.
- **redis** — real Redis (the state store's Layer 1). Swap the app's state store
  from in-memory to the real Redis adapter via config/env.
- **postgres** — real Postgres for durable data (the audit log / command history /
  anything currently in-memory that should persist). If a real
  SQLAlchemy/Postgres repository doesn't exist yet for a given aggregate, either
  implement it here or **flag it as a marked seam** and keep the in-memory adapter
  for now — disclose which.
- **mlflow** — an MLflow tracking server backed by Postgres (or its own volume)
  with an artifact store, so the model registries point at it.
- Wire everything with a shared network, healthchecks, and `depends_on` so startup
  order is correct (api waits for redis/postgres/mlflow to be healthy).
- All connection details come from **environment variables** (a committed
  `.env.example`, never real secrets in the image or compose file).

## 4. Selecting real vs in-memory adapters
- The composition root (`platform/`) chooses adapters based on config/env:
  in-memory for tests/local-fast, real (Redis/Postgres/MLflow) when the env says
  so. Add a clear `SOLAROPS_ENV` (or similar) switch. Tests keep using the
  in-memory/fake path and must stay green — **do not make the test suite depend on
  running containers.**

## 5. Monitoring
- Fold the existing `docker-compose.monitoring.yml` (Prometheus + Grafana) into
  the main compose, or document running them together, so `docker compose up`
  optionally includes monitoring. Prometheus scrapes the api service by its
  compose service name.

## 6. Docs
- Update the root `README.md` (and/or a `DEPLOYMENT.md`) with:
  - one-command local run: `docker compose up`,
  - the URLs (API `/docs`, Grafana),
  - how to point the dashboard at the containerised API,
  - the env vars and where to copy `.env.example`.

## 7. Definition of done
- `docker compose up` from a clean checkout brings up api + redis + postgres +
  mlflow (+ monitoring) with correct startup ordering; the API `/docs` is
  reachable and a decision-cycle → approval → completion works against the real
  Redis/Postgres.
- Real adapters are used inside the containers; the test suite still runs on the
  in-memory/fake path and stays green (`pytest`, `ruff`, `lint-imports`).
- No secrets committed; `.env.example` documents every variable.
- Any aggregate still on an in-memory repo (not yet persisted to Postgres) is
  disclosed as a marked seam, not hidden.
- **Report:** files created, what now runs in real containers vs still in-memory
  (be explicit), the exact run command and URLs, any real-infrastructure issues
  found and how they were resolved, and test results.