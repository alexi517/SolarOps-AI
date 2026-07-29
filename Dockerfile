# SolarOps AI — API container (Phase 8 brief §2).
#
# Single-instance by design: SystemComposition is an in-process singleton
# holding its own DigitalTwin and in-memory registries/repositories (see
# DEPLOYMENT.md "Known constraints"). Running more than one uvicorn worker,
# or more than one replica of this container against the same site, would
# give each process its own diverging twin — do not add --workers or scale
# replicas > 1 without first moving twin/state ownership out of the process.
FROM python:3.12-slim AS base

RUN useradd --create-home --uid 1000 app
WORKDIR /app

# Dependencies first, in their own layer — `pyproject.toml` changes far less
# often than application code, so this layer stays cached across most builds.
COPY pyproject.toml ./
COPY src/solarops/__init__.py src/solarops/__init__.py
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Now the real source, invalidating only from here down on code changes.
COPY src/ src/
RUN pip install --no-cache-dir --no-deps .

USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

CMD ["uvicorn", "solarops.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
