"""AnomalyConfig — every tunable in one place (Phase 6b brief §3/§4/§5).

Rule thresholds, statistical sigma threshold, severity buckets, Isolation
Forest parameters, and the Document 6 §5 evaluation targets all live here —
mirrors ``forecast.infrastructure.config.ForecastConfig``'s pattern (Doc 8
§10), which the domain/application layers already import directly by
established precedent in this codebase.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["AnomalyConfig"]


class AnomalyConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ANOMALY_", env_file=".env", extra="ignore")

    site_id: str = "site-001"

    # --- Rule detector thresholds (brief §4) ---
    battery_overheat_temp_c: float = 45.0
    grid_instability_statuses: tuple[str, ...] = ("OUTAGE", "UNSTABLE")
    inverter_fault_statuses: tuple[str, ...] = (
        "FAULT_OVERTEMP",
        "FAULT_OVERVOLTAGE",
        "SHUTDOWN",
    )
    inverter_comm_loss_statuses: tuple[str, ...] = ("FAULT_COMM_LOSS",)

    # --- Statistical detector (brief §4) ---
    load_spike_sigma_threshold: float = 3.0
    sensor_dropout_min_history: int = 10
    min_history_for_baseline: int = 5

    # --- Isolation Forest (brief §4). ``contamination`` is a numeric target
    # false-positive rate, not scikit-learn's ``"auto"`` — measured directly
    # against real twin-generated history (thousands of readings, brief §7),
    # "auto"'s fixed score threshold from the original Isolation Forest paper
    # self-flagged ~36% of genuinely normal training readings as anomalous,
    # badly miscalibrated for this feature space. A numeric contamination
    # needs a reasonably large, representative training set to be reliable —
    # too small (tens of readings) and the percentile estimate is noisy in
    # the other direction. ---
    isolation_forest_contamination: float = 0.05
    isolation_forest_n_estimators: int = 100
    isolation_forest_random_state: int = 42
    lookback_hours: float = 24.0

    # --- Severity buckets (brief §3: "keep the scale in config") ---
    critical_confidence_threshold: float = 0.85
    warning_confidence_threshold: float = 0.6

    # --- Evaluation & release gate (brief §5, Document 6 §5) ---
    precision_target: float = 0.90
    recall_target: float = 0.90
    detection_delay_target_seconds: float = 10.0
