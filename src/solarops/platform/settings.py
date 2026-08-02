"""Real vs in-memory adapter selection (Phase 8 brief §4).

``SOLAROPS_ENV`` is the one switch: "local" (default — every test and local
`.venv` run) keeps the in-memory/fake path exactly as it's always been;
"production" (set by the ``api`` service in ``docker-compose.yml``) selects
Redis/Postgres/MLflow. No test sets ``SOLAROPS_ENV`` or constructs
``PlatformSettings`` with real-service URLs, so this file is never on any
test's import path in a way that could make a test depend on a container —
``build_system_composition()`` reads it once, at composition-root level,
mirroring the existing ``api/dependencies.py::APISettings`` pattern exactly.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["PlatformSettings"]


class PlatformSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOLAROPS_", env_file=".env", extra="ignore")

    env: str = "local"
    redis_url: str = "redis://localhost:6379/0"
    postgres_dsn: str = "postgresql+psycopg://solarops:solarops@localhost:5432/solarops"
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Off (0) by default: this changes real runtime behavior (commands can
    # get dispatched with nobody watching), so it must be turned on
    # deliberately, not silently inherited from a default. When > 0, a
    # background loop calls SystemComposition.run_decision_cycle() on this
    # interval — the risk-based auto-execute policy (RiskLevel) still
    # decides which resulting commands need a human; this only decides
    # whether the *cycle itself* runs without one.
    auto_decision_cycle_seconds: float = 0.0

    # Both empty by default (disabled) — a CallMeBot-backed WhatsApp
    # notifier (platform/notifications.py) is only wired in once both are
    # set; otherwise every notification is silently a no-op (NullNotifier).
    whatsapp_phone: str = ""
    whatsapp_api_key: str = ""

    @property
    def use_real_infra(self) -> bool:
        return self.env == "production"

    @property
    def whatsapp_configured(self) -> bool:
        return bool(self.whatsapp_phone and self.whatsapp_api_key)
