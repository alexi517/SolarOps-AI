from datetime import UTC, datetime

import pytest

from solarops.forecast.domain.forecast_metadata import ForecastMetadata

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_metadata(**overrides):
    defaults = dict(
        model_name="solar-baseline",
        model_version="v1",
        generated_at=NOW,
        horizon_minutes=360,
        resolution_minutes=15,
    )
    defaults.update(overrides)
    return ForecastMetadata(**defaults)


def test_constructs_with_valid_fields():
    metadata = make_metadata()
    assert metadata.model_name == "solar-baseline"
    assert metadata.confidence is None


def test_rejects_confidence_outside_unit_interval():
    with pytest.raises(ValueError, match="confidence"):
        make_metadata(confidence=1.5)


def test_rejects_nonpositive_horizon():
    with pytest.raises(ValueError, match="horizon_minutes"):
        make_metadata(horizon_minutes=0)


def test_rejects_nonpositive_resolution():
    with pytest.raises(ValueError, match="resolution_minutes"):
        make_metadata(resolution_minutes=0)
