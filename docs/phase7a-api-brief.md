# Phase 7a Brief — The API (front door)

**For:** Claude Code (or manual execution)
**Scope:** The HTTP API only. The dashboard (7b) and monitoring (7c) follow.
**Source of truth:** the architecture documents (CESF §16 for security; Document 6
§11 for the ops metrics that 7c will expose).

**IMPORTANT — save this file to `docs/phase7a-api-brief.md` before building.** Read
it alongside `docs/08-domain-driven-design-spec.md`.

## 0. What this is
A thin FastAPI layer that exposes the system that already exists. It contains
**no business logic** — it calls the existing application services and maps their
results to/from JSON. This is the edge/adapter layer (Doc 8): like `platform`, the
`api` package is a composition edge and **may import multiple contexts**. Add/adjust
the import-linter contract accordingly, and confirm no *context* imports `api`.

## 1. Where it lives
`src/solarops/api/` — `app.py` (the FastAPI app + wiring), `routers/` (one per
area), `schemas/` (Pydantic request/response DTOs — Pydantic belongs here, at the
edge, doing serialization), `dependencies.py` (DI: hand routers the wired services
from `platform`), `errors.py` (map domain exceptions → HTTP status codes).

## 2. Endpoints (thin — each calls an existing service)
**State**
- `GET /sites/{site_id}/state` → current `EnergyState` (`StateManager.get_current`).

**Forecasts**
- `GET /sites/{site_id}/forecasts` → latest forecasts. Reflect reality honestly:
  only solar is registered; load/battery show as unavailable, not faked.

**Anomalies**
- `GET /sites/{site_id}/anomalies` → recent anomalies/alerts, with their six fields.

**Decisions**
- `GET /sites/{site_id}/recommendations` → latest ranked recommendations.
- `POST /sites/{site_id}/decision-cycle` → run one reasoning cycle now and return
  the recommendations (useful for a live demo).

**Commands & audit**
- `GET /sites/{site_id}/commands` → command list with current status.
- `GET /commands/{command_id}` → one command's full detail and lifecycle.
- `GET /commands/{command_id}/audit` → the immutable audit trail.

**Human approval (this completes the Phase 5 HITL workflow — the key part)**
- `GET /sites/{site_id}/approvals/pending` → commands paused awaiting approval.
- `POST /approvals/{approval_id}/approve`
- `POST /approvals/{approval_id}/reject`
- `POST /approvals/{approval_id}/modify` → adjust target, then approve.
These call the existing `ApprovalEngine` / `ApprovalRequest` aggregate. Until now
the approve/reject/modify step existed only in code — these endpoints make it real.

**Ops**
- `GET /health` → liveness.
- `GET /metrics` → Prometheus format. Stub in 7a (a couple of basic counters);
  fully populated in 7c from the CESF §17 / Document 6 §11 metric list.

## 3. Design fork — CONFIRM (security)
CESF §16 requires authenticated, role-based, authorised requests. Full RBAC is
heavy for a demo. Two options:
- **Option A (recommended for now):** a minimal API-key dependency on the
  mutating endpoints (the approval POSTs), with a clearly-marked `TODO(auth-rbac)`
  seam citing CESF §16. Read endpoints open in the demo.
- **Option B:** implement full authentication + role-based authorisation now.
Build **Option A** unless the PRD/SAS specifies otherwise; do not silently ship
*no* auth on the approval actions — that's the one place it matters even in a demo.

## 4. Contracts & correctness
- DTOs are Pydantic models; map kernel value objects to plain JSON (numbers,
  strings) in the schema layer — serialization is the edge's job, not the domain's.
- Map domain exceptions to sensible HTTP codes (e.g. `PolicyViolation`/
  `SafetyViolation` → 409/422; not-found → 404; `FailSafeTriggered` → 503).
- In-memory repositories are fine for 7a — standing up real Redis/Postgres/MLflow
  via Docker is the 7c "wire it for real" pass, not this one.
- OpenAPI docs (FastAPI's automatic `/docs`) should come out clean and browsable —
  that Swagger page is itself a great demo artifact.

## 5. Import rules
- `solarops.api` may import the application services it needs (via `platform`
  wiring) — it is an edge. Add the contract; confirm **no bounded context imports
  `api`** (dependencies point inward, toward the domain).
- Run `lint-imports` and confirm all contracts still hold.

## 6. Definition of done (7a)
- The endpoints above work against the running system; `/docs` renders a clean,
  browsable OpenAPI page.
- The approval endpoints drive a real command that is paused awaiting approval:
  approving it lets it proceed through the Phase 5 pipeline; rejecting it
  terminates it — demonstrated end to end.
- Domain exceptions map to correct HTTP codes; the API contains no business logic.
- Auth: Option A on the approval POSTs, with the RBAC seam marked.
- `pytest` (add API tests via FastAPI's `TestClient`), `ruff`, `lint-imports` green.
- **Report:** files created, the endpoint list, a plain-English walkthrough of
  approving one command through the API, and test results. Stop before 7b.