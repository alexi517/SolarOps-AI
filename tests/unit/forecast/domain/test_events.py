from solarops.forecast.domain.events import ForecastGenerated
from solarops.forecast.domain.forecast_kind import ForecastKind


def test_forecast_generated_carries_model_provenance():
    event = ForecastGenerated(
        aggregate_id="FC-1",
        aggregate_type="Forecast",
        kind=ForecastKind.SOLAR_GENERATION,
        model_name="solar-baseline",
        model_version="v1",
        horizon_minutes=360,
    )
    assert event.event_type == "ForecastGenerated"
    assert event.kind is ForecastKind.SOLAR_GENERATION
