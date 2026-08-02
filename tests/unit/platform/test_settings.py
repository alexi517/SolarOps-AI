"""PlatformSettings — the SOLAROPS_ENV switch between in-memory/fake
adapters (every test's path) and real Redis/Postgres/MLflow (Phase 8 brief
§4). ``_env_file=None`` makes these hermetic regardless of whether a real
``.env`` happens to exist on disk — the same defensive override the brief's
own "tests must stay on the in-memory/fake path" requirement calls for.
"""

from __future__ import annotations

from solarops.platform.settings import PlatformSettings


def test_defaults_to_local_and_in_memory_adapters(monkeypatch):
    monkeypatch.delenv("SOLAROPS_ENV", raising=False)

    settings = PlatformSettings(_env_file=None)

    assert settings.env == "local"
    assert settings.use_real_infra is False


def test_production_env_selects_real_infra(monkeypatch):
    monkeypatch.setenv("SOLAROPS_ENV", "production")

    settings = PlatformSettings(_env_file=None)

    assert settings.env == "production"
    assert settings.use_real_infra is True


def test_auto_decision_cycle_is_off_by_default(monkeypatch):
    monkeypatch.delenv("SOLAROPS_AUTO_DECISION_CYCLE_SECONDS", raising=False)

    settings = PlatformSettings(_env_file=None)

    assert settings.auto_decision_cycle_seconds == 0.0


def test_auto_decision_cycle_interval_is_overridable_via_env(monkeypatch):
    monkeypatch.setenv("SOLAROPS_AUTO_DECISION_CYCLE_SECONDS", "300")

    settings = PlatformSettings(_env_file=None)

    assert settings.auto_decision_cycle_seconds == 300.0


def test_whatsapp_is_unconfigured_by_default(monkeypatch):
    monkeypatch.delenv("SOLAROPS_WHATSAPP_PHONE", raising=False)
    monkeypatch.delenv("SOLAROPS_WHATSAPP_API_KEY", raising=False)

    settings = PlatformSettings(_env_file=None)

    assert settings.whatsapp_configured is False


def test_whatsapp_is_configured_only_once_both_phone_and_key_are_set(monkeypatch):
    monkeypatch.setenv("SOLAROPS_WHATSAPP_PHONE", "1234567890")
    monkeypatch.delenv("SOLAROPS_WHATSAPP_API_KEY", raising=False)
    assert PlatformSettings(_env_file=None).whatsapp_configured is False

    monkeypatch.setenv("SOLAROPS_WHATSAPP_API_KEY", "abc123")
    assert PlatformSettings(_env_file=None).whatsapp_configured is True


def test_connection_settings_are_overridable_via_env(monkeypatch):
    monkeypatch.setenv("SOLAROPS_REDIS_URL", "redis://example:6379/1")
    monkeypatch.setenv("SOLAROPS_POSTGRES_DSN", "postgresql+psycopg://u:p@example/db")
    monkeypatch.setenv("SOLAROPS_MLFLOW_TRACKING_URI", "http://example:5000")

    settings = PlatformSettings(_env_file=None)

    assert settings.redis_url == "redis://example:6379/1"
    assert settings.postgres_dsn == "postgresql+psycopg://u:p@example/db"
    assert settings.mlflow_tracking_uri == "http://example:5000"
