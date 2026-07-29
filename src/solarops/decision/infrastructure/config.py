"""RuleEngineConfig — every v1 rule-engine tunable in one place (Phase 6c brief §5).

Mirrors ``forecast.infrastructure.config.ForecastConfig`` / ``anomaly.infrastructure
.config.AnomalyConfig``'s pattern: thresholds the engine reasons with, never
hardcoded in ``rule_based_optimiser.py``. These are the engine's own *soft*
preferences (e.g. a comfortable SOC band) — distinct from ``OperatingConstraints``'
*hard* bounds, which come from the real Policy/SafetyLimits via platform wiring.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["RuleEngineConfig"]


class RuleEngineConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DECISION_", env_file=".env", extra="ignore")

    # --- Priority 3: battery health — a comfortable band, softer than the
    # hard Policy/SafetyLimits bounds in OperatingConstraints. ---
    battery_healthy_min_soc_pct: float = 30.0
    battery_healthy_max_soc_pct: float = 85.0
    reserve_charge_power_kw: float = 10.0

    # --- Priority 2: reliability during a grid outage ---
    reliability_min_discharge_margin_pct: float = 5.0
    load_shed_fraction_on_outage: float = 0.2

    # --- Priority 4: self-consumption ---
    self_consumption_min_surplus_kw: float = 0.5

    # --- Priority 5: cost / import minimisation ---
    cost_discharge_margin_pct: float = 10.0
    cost_discharge_power_kw: float = 5.0

    # --- Phase 6d: confidence estimation (Document 9 §8) — a real weighted
    # score computed by ConfidenceEstimator, replacing the old fixed
    # per-priority values. Weights sum to 1.0.
    #
    # Calibrated (Phase 7c) so the system's permanent, known, already-
    # disclosed capability gap — only solar forecasting has ever passed
    # evaluation (Phase 6a); load/battery-SOC forecasts are structurally
    # never registered — lands solidly in Medium, not Low. Low is reserved
    # for genuinely situational problems: stale telemetry or active
    # anomalies. Forecast certainty/completeness are weighted down
    # accordingly; freshness/anomaly-presence (which stay at their perfect
    # 1.0 baseline in ordinary healthy operation, and only drop when
    # something is actually wrong) carry more weight instead. ---
    confidence_weight_forecast_certainty: float = 0.20
    confidence_weight_data_freshness: float = 0.35
    confidence_weight_input_completeness: float = 0.10
    confidence_weight_anomaly_presence: float = 0.35

    confidence_band_high_threshold: float = 0.90
    confidence_band_low_threshold: float = 0.70

    # Forecast-certainty sub-score fallbacks.
    confidence_unavailable_forecast_subscore: float = 0.3
    confidence_missing_metadata_subscore: float = 0.7

    # Data-freshness sub-score: 1.0 under the fresh bound, a 0.2 floor at
    # or beyond the stale bound, linear in between.
    confidence_state_fresh_seconds: float = 60.0
    confidence_state_stale_seconds: float = 900.0

    # Anomaly-presence sub-score: 1.0 - penalty * count, floored.
    confidence_anomaly_penalty_per_anomaly: float = 0.25
    confidence_anomaly_min_subscore: float = 0.3

    # Document 9 §12 — conservative under uncertainty: under Low confidence,
    # the top-priority candidate's own magnitude is scaled down by this
    # factor (a smaller version of the *same* action — priority order is
    # never disturbed, so a minor priority like cost-minimisation can never
    # leapfrog a more important one just for being numerically smaller).
    confidence_low_conservative_scale: float = 0.5
