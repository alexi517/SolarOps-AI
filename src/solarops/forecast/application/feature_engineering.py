"""feature_engineering — raw history + current EnergyState -> per-kind FeatureSet (brief §3, §5).

Only Solar Generation and Building Load read straight off telemetry; Battery
SOC's features are assembled separately by ``BatterySocForecaster`` from the
*other two* forecasts (see its module docstring) — this module covers the two
telemetry-driven kinds.
"""

from __future__ import annotations

from collections.abc import Callable

from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["build_features"]


def build_features(
    kind: ForecastKind,
    current: EnergyState,
    history: list[EnergyState],
    config: ForecastConfig,
) -> FeatureSet:
    """Build the FeatureSet for ``kind``, restricted to ``config``'s configured feature names.

    ``history`` should be ordered oldest-first and cover ``config.lookback_hours``
    (the caller — typically a ``HistoricalDataSource`` — is responsible for that
    window); it feeds the trailing-average "historical output/demand" inputs.
    """
    if kind is ForecastKind.SOLAR_GENERATION:
        available = _solar_signals(current, history)
        names = config.solar_features
    elif kind is ForecastKind.BUILDING_LOAD:
        available = _load_signals(current, history)
        names = config.load_features
    else:
        raise ValueError(f"build_features does not handle {kind} — see BatterySocForecaster")

    values = {name: available[name] for name in names}
    return FeatureSet(kind=kind, as_of=current.timestamp, values=values)


def _hour_of_day(state: EnergyState) -> float:
    ts = state.timestamp
    return ts.hour + ts.minute / 60.0


def _day_of_week(state: EnergyState) -> float:
    return float(state.timestamp.weekday())


def _is_weekend(state: EnergyState) -> float:
    return 1.0 if state.timestamp.weekday() >= 5 else 0.0


def _day_of_year(state: EnergyState) -> float:
    return float(state.timestamp.timetuple().tm_yday)


def _trailing_avg(history: list[EnergyState], value_of: Callable[[EnergyState], float]) -> float:
    if not history:
        return 0.0
    return sum(value_of(s) for s in history) / len(history)


def _solar_signals(current: EnergyState, history: list[EnergyState]) -> dict[str, float]:
    return {
        "solar_power_kw": current.solar_power.value,
        "solar_power_trailing_avg_kw": _trailing_avg(history, lambda s: s.solar_power.value),
        "irradiance_w_m2": current.irradiance_w_m2,
        "cloud_cover_pct": current.cloud_cover_pct,
        "ambient_temp_c": current.ambient_temp.value,
        "hour_of_day": _hour_of_day(current),
        "day_of_year": _day_of_year(current),
    }


def _load_signals(current: EnergyState, history: list[EnergyState]) -> dict[str, float]:
    trailing_avg = _trailing_avg(history, lambda s: s.building_load.value)
    peak_observed = max(
        (s.building_load.value for s in history), default=current.building_load.value
    )
    peak_observed = max(peak_observed, current.building_load.value)
    occupancy_proxy = current.building_load.value / peak_observed if peak_observed > 0 else 0.0
    return {
        "building_load_kw": current.building_load.value,
        "building_load_trailing_avg_kw": trailing_avg,
        "building_load_peak_observed_kw": peak_observed,
        "hour_of_day": _hour_of_day(current),
        "day_of_week": _day_of_week(current),
        "is_weekend": _is_weekend(current),
        "occupancy_proxy": occupancy_proxy,
    }
