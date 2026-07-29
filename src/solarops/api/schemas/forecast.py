"""Forecast -> JSON. Brief §2: reflect reality honestly — only Solar is
production-registered (6a); Load/Battery-SOC show as unavailable, never faked."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from solarops.forecast.domain.forecast import Forecast

__all__ = [
    "ForecastPointResponse",
    "ForecastResponse",
    "ForecastAvailabilityResponse",
    "SiteForecastsResponse",
]


class ForecastPointResponse(BaseModel):
    timestamp: datetime
    value: float
    interval_low: float | None = None
    interval_high: float | None = None


class ForecastResponse(BaseModel):
    forecast_id: str
    kind: str
    horizon_minutes: int
    model_name: str
    model_version: str
    generated_at: datetime
    confidence: float | None
    points: list[ForecastPointResponse]

    @classmethod
    def from_domain(cls, forecast: Forecast) -> ForecastResponse:
        return cls(
            forecast_id=str(forecast.forecast_id),
            kind=forecast.kind.value,
            horizon_minutes=forecast.horizon_minutes,
            model_name=forecast.metadata.model_name,
            model_version=forecast.metadata.model_version,
            generated_at=forecast.metadata.generated_at,
            confidence=forecast.metadata.confidence,
            points=[
                ForecastPointResponse(
                    timestamp=point.timestamp,
                    value=point.value.value,
                    interval_low=point.interval_low,
                    interval_high=point.interval_high,
                )
                for point in forecast.points
            ],
        )


class ForecastAvailabilityResponse(BaseModel):
    kind: str
    available: bool
    forecast: ForecastResponse | None = None
    reason: str | None = None


class SiteForecastsResponse(BaseModel):
    site_id: str
    forecasts: list[ForecastAvailabilityResponse]
