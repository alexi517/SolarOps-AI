# Deployment (Phase 8)

`docker compose up` brings up the whole platform wired to real
infrastructure — no manual `.venv` steps. This doc covers running it, what
each piece is, and the constraints worth knowing before putting it anywhere
beyond a single local/demo machine.

## Run it

```
cp .env.example .env        # edit if you want non-default credentials
docker compose up --build
```

That starts four services: `api`, `redis`, `postgres`, `mlflow`. Add
monitoring:

```
docker compose --profile monitoring up --build
```

which additionally starts `prometheus` and `grafana`.

## URLs

| Service | URL | Notes |
|---|---|---|
| API docs | http://localhost:8000/docs | Interactive OpenAPI page |
| API health | http://localhost:8000/health | Used by the container healthcheck |
| API metrics | http://localhost:8000/metrics | Real Prometheus exposition format |
| MLflow | http://localhost:5000 | Forecast/anomaly model registry + experiment tracking |
| Prometheus (`--profile monitoring`) | http://localhost:9090 | Status → Targets should show `solarops-api` as `UP` |
| Grafana (`--profile monitoring`) | http://localhost:3000 | `admin` / `admin` — change if exposed beyond local use |

## Pointing the dashboard at the containerized API

Nothing to change. `dashboard/config.py` already defaults
`SOLAROPS_API_BASE_URL` to `http://127.0.0.1:8000` (Phase 7b), and the `api`
service publishes that same port to the host (`ports: ["8000:8000"]`), so
`streamlit run dashboard/app.py` on the host talks to the containerized API
exactly as it would talk to `python scripts/run_api.py`. Only override
`SOLAROPS_API_BASE_URL` if you're running the API on a different host/port.

## Environment variables

Every variable is documented with a placeholder value in `.env.example` —
copy it to `.env` before running compose (`.env` is git-ignored; never commit
real credentials). Summary:

| Variable | Used by | Purpose |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `postgres`, and composed into the DSNs below | Postgres init + credentials |
| `SOLAROPS_ENV` | `api` (`platform/settings.py`) | `local` (default, in-memory/fake — what tests always use) or `production` (real Redis/Postgres/MLflow). `docker-compose.yml` sets this to `production` for the `api` service directly; the value in `.env`/`.env.example` only matters if you run the API outside compose. |
| `SOLAROPS_REDIS_URL` | `api` | Redis connection string (`redis://redis:6379/0` inside compose) |
| `SOLAROPS_POSTGRES_DSN` | `api` | Postgres connection string for the audit log (built from the `POSTGRES_*` vars inside `docker-compose.yml`) |
| `SOLAROPS_MLFLOW_TRACKING_URI` | `api` | Where the forecast/anomaly model registries log to (`http://mlflow:5000` inside compose) |
| `SOLAROPS_API_KEY` | `api`, dashboard | Shared-secret auth on the mutating approval endpoints (Phase 7a §3) |

## What runs on real infrastructure now, vs. what's still in-memory

`SOLAROPS_ENV=production` (set automatically for the `api` service in
`docker-compose.yml`) switches these three:

| Concern | Real adapter | In-memory (SOLAROPS_ENV=local, e.g. every test) |
|---|---|---|
| Telemetry state store (Layer 1) | `RedisStateStore` → real Redis | `InMemoryStateStore` |
| Audit log (CESF §15) | `PostgresAuditLog` → real Postgres | `InMemoryAuditLog` |
| Forecast model registry | `MLflowModelRegistry` → real MLflow server | `InMemoryModelRegistry` |
| Anomaly detector registry | `MLflowDetectorRegistry` → real MLflow server | `InMemoryDetectorRegistry` |

**Marked seams — still in-memory even with `SOLAROPS_ENV=production`,
disclosed rather than hidden:**

| Concern | Why it's still in-memory |
|---|---|
| `CommandRepository` | `Command` is a rich state-machine aggregate — 6 nested gate-outcome objects (policy/safety/risk/approval/execution/verification results) behind a strict forward-only transition API with no "load into an arbitrary state" path. Persisting it faithfully needs transition-replay logic on load, which couldn't be integration-tested against a real Postgres in the environment this was built in. Restarting the `api` container loses in-flight commands. |
| `ApprovalRequestRepository` | Same shape of risk as `Command` — its own async, long-lived lifecycle (ADR-017), same reconstruction problem. |
| `PolicyRepository`, `ForecastRepository`, `AnomalyRepository`, `AlertPublisher` | Not named in the brief's persistence targets; unchanged from every earlier phase. |

If/when Command/ApprovalRequest persistence is worth doing, the honest path
is a snapshot+replay adapter reviewed and tested against a real Postgres
instance — not a guess shipped without one.

## Known constraints

- **Single instance only.** `SystemComposition` is an in-process singleton —
  it owns one `DigitalTwin` and every still-in-memory registry/repository
  directly. Running more than one `uvicorn` worker (`--workers`) or more
  than one replica of the `api` service would give each process its own
  diverging twin and its own copy of the in-memory state above. The
  Dockerfile deliberately runs a single worker; don't scale this past one
  instance without first moving twin/state ownership out of the process.
- **Shared Postgres database.** `postgres` hosts one database (`POSTGRES_DB`,
  default `solarops`) used both for the app's `audit_log` table and MLflow's
  own backend-store tables (experiments, runs, model versions). They don't
  collide — MLflow manages its own table names — but if you'd rather isolate
  them, point `SOLAROPS_POSTGRES_DSN` and `MLFLOW_BACKEND_STORE_URI` at
  separate databases; nothing in the code assumes they're the same one.
- **MLflow runs from a small custom image** (`docker/mlflow.Dockerfile`:
  `python:3.12-slim` + `pip install mlflow psycopg2-binary`), not an
  unverified community image, so every layer is reviewable in this repo.
- **No secrets in the image.** The Dockerfile never copies `.env`; all
  connection details are injected at container start via `environment:` in
  `docker-compose.yml`.

## What was verified vs. not

Docker cannot run in the environment this was built in (virtualization/WSL
blocked). Verified: `pytest`, `ruff check`, `lint-imports` — all against the
unchanged in-memory/fake path (`SOLAROPS_ENV` unset ⇒ `local`), since no test
sets it. **Not verified**: `docker compose up` actually starting, any
container healthcheck passing, or a decision-cycle → approval → completion
flow against the real Redis/Postgres/MLflow. Every Docker/compose file here
was written and reviewed for correctness by hand — the definition-of-done
container run itself is the one thing that needs a machine that can run
Docker.
