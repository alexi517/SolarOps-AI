from datetime import UTC, datetime, timedelta

import pytest

from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_metadata import ForecastMetadata
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import ForecastId, Power, SiteId

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
SITE_ID = SiteId("SITE-1")


def make_forecast(points=None, **overrides):
    if points is None:
        points = [
            ForecastPoint(timestamp=NOW + timedelta(minutes=m), value=Power(float(m)))
            for m in (0, 15, 30, 45, 60)
        ]
    defaults = dict(
        forecast_id=ForecastId.generate(),
        site_id=SITE_ID,
        kind=ForecastKind.SOLAR_GENERATION,
        horizon_minutes=60,
        points=tuple(points),
        metadata=ForecastMetadata(
            model_name="solar-baseline",
            model_version="v1",
            generated_at=NOW,
            horizon_minutes=60,
            resolution_minutes=15,
        ),
    )
    defaults.update(overrides)
    return Forecast(**defaults)


def test_constructs_with_ordered_points():
    forecast = make_forecast()
    assert len(forecast.points) == 5
    assert forecast.kind is ForecastKind.SOLAR_GENERATION


def test_rejects_empty_points():
    with pytest.raises(ValueError, match="empty"):
        make_forecast(points=[])


def test_rejects_unordered_points():
    unordered = [
        ForecastPoint(timestamp=NOW + timedelta(minutes=30), value=Power(1.0)),
        ForecastPoint(timestamp=NOW, value=Power(2.0)),
    ]
    with pytest.raises(ValueError, match="ordered"):
        make_forecast(points=unordered)


def test_at_horizon_returns_closest_point_without_exceeding():
    forecast = make_forecast()
    point = forecast.at_horizon(30)
    assert point.timestamp == NOW + timedelta(minutes=30)


def test_at_horizon_clamps_to_earliest_point_when_before_series():
    points = [ForecastPoint(timestamp=NOW + timedelta(minutes=15), value=Power(1.0))]
    forecast = make_forecast(points=points, horizon_minutes=15)
    point = forecast.at_horizon(0)
    assert point.timestamp == NOW + timedelta(minutes=15)


def test_generated_at_matches_metadata():
    forecast = make_forecast()
    assert forecast.generated_at == NOW


def test_is_immutable():
    forecast = make_forecast()
    with pytest.raises(Exception):
        forecast.kind = ForecastKind.BUILDING_LOAD  # type: ignore[misc]
