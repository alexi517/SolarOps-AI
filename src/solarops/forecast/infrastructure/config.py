"""ForecastConfig — every tunable in one place (Phase 6a brief §4/§5/§6).

Horizons, resolution, per-kind feature lists, the battery energy-balance
parameters, and the Document 6 evaluation targets all live here so behaviour
is swappable without touching code — mirrors ``simulation.infrastructure.config``'s
``SiteConfig``/``SimulatorConfig`` pattern (Doc 8 §10), which the domain layer
already imports directly by established precedent in this codebase
(``simulation/domain/digital_twin.py``).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["ForecastConfig"]


class ForecastConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FORECAST_", env_file=".env", extra="ignore")

    site_id: str = "site-001"

    # --- Horizons (brief §5): 15 min, 30 min, 1 h, 6 h checkpoints, evaluated
    # against a series produced at ``resolution_minutes`` spacing out to the max. ---
    horizon_labels: tuple[str, ...] = ("15min", "30min", "1h", "6h")
    horizons_minutes: tuple[int, ...] = (15, 30, 60, 360)
    resolution_minutes: int = 15

    @property
    def max_horizon_minutes(self) -> int:
        return max(self.horizons_minutes)

    @property
    def named_horizons(self) -> dict[str, int]:
        return dict(zip(self.horizon_labels, self.horizons_minutes, strict=True))

    # --- Per-kind feature inputs (brief §5). ``*_trailing_avg_*`` are the
    # "historical output/demand" inputs, computed by feature_engineering.py
    # over the ``HistoricalDataSource`` lookback window; everything else is
    # read off the current ``EnergyState`` or derived from its timestamp. ---
    solar_features: tuple[str, ...] = (
        "solar_power_kw",
        "solar_power_trailing_avg_kw",
        "irradiance_w_m2",
        "cloud_cover_pct",
        "ambient_temp_c",
        "hour_of_day",
        "day_of_year",
    )
    load_features: tuple[str, ...] = (
        "building_load_kw",
        "building_load_trailing_avg_kw",
        "building_load_peak_observed_kw",
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "occupancy_proxy",
    )

    # Battery SOC's baseline is an energy-balance projection driven by the
    # *other two* forecasts (brief §5), not raw telemetry — its FeatureSet
    # carries current SOC plus the average solar/load expected over the
    # projection horizon, computed by BatterySocForecaster from the Solar and
    # Load Forecast objects it is handed.
    battery_features: tuple[str, ...] = (
        "current_soc_pct",
        "avg_expected_solar_kw",
        "avg_expected_load_kw",
    )

    # --- Battery SOC energy-balance model (brief §5) — Forecast's own copy of
    # the physical parameters, since it may not import Simulation's SiteConfig
    # (Phase 6a brief §8). Wired from the real SiteConfig at the platform
    # composition root (see platform/forecast_wiring.py), never duplicated by hand. ---
    battery_capacity_kwh: float = 200.0
    battery_round_trip_efficiency: float = 0.92

    # --- Evaluation & release gate (brief §6, Document 6 §4). Document 6 gives
    # Solar MAE as a percentage target, but MAE on ``Power`` is naturally in kW
    # — ``solar_capacity_kw`` normalises raw MAE into a percentage-of-capacity
    # figure comparable to the target. Load MAPE is already a percentage by
    # definition; Battery SOC MAE is already on the 0-100 SOC-percentage scale,
    # so neither needs normalising. ---
    solar_capacity_kw: float = 100.0
    solar_mae_target_pct: float = 8.0
    load_mape_target_pct: float = 10.0
    battery_soc_error_target_pct: float = 5.0

    # How much history feature engineering / training draws on.
    lookback_hours: float = 72.0
