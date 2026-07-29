# MLflow tracking server (Phase 8 brief §3) — a small, self-authored image
# rather than an unverified community one, so every layer here is reviewable
# in this repo. Pinned to the same major version range as the `mlflow`
# dependency in pyproject.toml so the client library (MLflowModelRegistry /
# MLflowDetectorRegistry) and server stay API-compatible.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "mlflow>=2,<3" psycopg2-binary

WORKDIR /mlflow
EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:5000/health || exit 1

# Shell form so $MLFLOW_BACKEND_STORE_URI/$MLFLOW_ARTIFACT_ROOT expand from
# the compose service's environment at container start.
CMD mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri "$MLFLOW_BACKEND_STORE_URI" \
    --default-artifact-root "$MLFLOW_ARTIFACT_ROOT"
