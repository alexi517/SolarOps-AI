"""SystemComposition — one wired world, built once per test module here
(the forecast/anomaly training gates it runs at construction cost real time)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from solarops.anomaly.domain.anomaly import Anomaly
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.severity import Severity
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.platform.api_composition import build_system_composition
from solarops.shared_kernel import AnomalyId, AssetId, RiskLevel


@pytest.fixture(scope="module")
def composition():
    return build_system_composition()


def test_build_wires_a_current_reading(composition):
    state = composition.state_manager.get_current(composition.site_id)
    assert state is not None
    assert state.site_id == composition.site_id


def test_only_solar_forecast_model_is_registered(composition):
    repository = composition.forecast_repository
    site_id = composition.site_id

    solar = repository.get_latest(site_id, ForecastKind.SOLAR_GENERATION)
    load = repository.get_latest(site_id, ForecastKind.BUILDING_LOAD)
    battery = repository.get_latest(site_id, ForecastKind.BATTERY_SOC)

    assert solar is not None
    assert load is None
    assert battery is None


def test_rule_and_statistical_detectors_are_registered_isolation_forest_is_not(composition):
    rule_covered = composition.anomaly_registry.covered_types("rule-detector")
    statistical_covered = composition.anomaly_registry.covered_types("statistical-detector")
    isolation_forest_covered = composition.anomaly_registry.covered_types(
        "isolation-forest-detector"
    )
    assert rule_covered  # at least one type passed the per-type gate (6b cleanup pass)
    assert statistical_covered
    assert isolation_forest_covered == frozenset()  # never registered — never passed


def test_refresh_telemetry_advances_the_reading(composition):
    first = composition.state_manager.get_current(composition.site_id)
    second = composition.refresh_telemetry()
    assert second.timestamp >= first.timestamp


def test_run_decision_cycle_produces_a_ranked_list_and_a_command(composition):
    ranked, command = composition.run_decision_cycle()
    assert ranked.top is not None
    assert command.site_id == composition.site_id
    assert command.risk_assessment is not None


def test_default_site_config_can_produce_a_pause_for_approval(composition):
    # Retrying real decision cycles and hoping one lands on HIGH risk isn't
    # reliable — under calm conditions (a common real state) risk stays LOW
    # no matter how many times you retry a call that barely advances
    # simulated time. Forcing Policy into maintenance mode (with an
    # override, so every action type still passes the Policy gate) makes
    # RiskAssessor classify HIGH unconditionally (see
    # safety/application/risk_assessor.py), independent of what Decision
    # actually recommends — the same approach as api/conftest.py's
    # ensure_pending_approval. The original policy is restored afterwards.
    original_policy = composition.policy_repository.get_current(composition.site_id)
    forced_policy = dataclasses.replace(
        original_policy, maintenance_mode=True, maintenance_override=True
    )
    composition.policy_repository.save(forced_policy)
    try:
        for _ in range(5):
            _ranked, command = composition.run_decision_cycle()
            if command.status.value == "AWAITING_APPROVAL":
                assert command.risk_assessment.level in (
                    RiskLevel.LOW,
                    RiskLevel.MEDIUM,
                    RiskLevel.HIGH,
                )
                return
        raise AssertionError("no cycle paused for approval after 5 attempts")
    finally:
        composition.policy_repository.save(original_policy)


def test_current_decision_context_reflects_a_real_active_anomaly(composition):
    # Phase 6d: the composition root is the one place allowed to see both
    # Anomaly and Decision — this proves that pass-through actually works,
    # using a real Anomaly saved to the same repository the API/detectors use.
    composition.refresh_telemetry()
    baseline = composition.current_decision_context()
    assert baseline is not None
    assert baseline.active_anomaly_count == 0

    anomaly = Anomaly(
        anomaly_id=AnomalyId.generate(),
        site_id=composition.site_id,
        detected_at=datetime.now(UTC),
        anomaly_type=AnomalyType.INVERTER_FAULT,
        severity=Severity.WARNING,
        confidence=0.9,
        affected_asset=AssetId(f"{composition.site_id}-inverter"),
        supporting_evidence=("fault_codes contains FAULT_OVERTEMP",),
        recommended_action="Inspect inverter cooling.",
    )
    composition.anomaly_repository.save(anomaly)

    context = composition.current_decision_context()
    assert context is not None
    assert context.active_anomaly_count == 1
