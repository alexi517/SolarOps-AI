from datetime import UTC, datetime

from solarops.decision.application.rule_based_optimiser import RuleBasedOptimiser
from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.decision.domain.recommendation import Recommendation
from solarops.decision.infrastructure.config import RuleEngineConfig
from solarops.shared_kernel import FixedClock, Power, SiteId, StateOfCharge, Temperature
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.workflow.graph import build_graph

from ..telemetry.domain.test_telemetry import make_telemetry


def make_constraints(**overrides) -> OperatingConstraints:
    defaults = dict(
        max_battery_soc=StateOfCharge(95.0),
        min_battery_soc=StateOfCharge(10.0),
        battery_max_temp=Temperature(45.0),
        battery_max_charge_power=Power(50.0),
        battery_max_discharge_power=Power(50.0),
        maintenance_mode=False,
        max_shed_fraction=0.5,
    )
    defaults.update(overrides)
    return OperatingConstraints(**defaults)


def test_graph_produces_a_recommendation_from_an_energy_state():
    clock = FixedClock(datetime(2026, 7, 27, 12, 0, tzinfo=UTC))
    engine = RuleBasedOptimiser(RuleEngineConfig(), clock)
    graph = build_graph(engine, make_constraints())
    telemetry = make_telemetry(site_id=SiteId("SITE-1"))
    energy_state = EnergyState.from_telemetry(telemetry, any_asset_offline=False)

    result = graph.invoke({"energy_state": energy_state})

    assert isinstance(result["recommendation"], Recommendation)
    assert result["energy_state"] == energy_state


def test_graph_passes_available_forecasts_through_to_the_engine():
    clock = FixedClock(datetime(2026, 7, 27, 12, 0, tzinfo=UTC))
    engine = RuleBasedOptimiser(RuleEngineConfig(), clock)
    graph = build_graph(engine, make_constraints())
    telemetry = make_telemetry(site_id=SiteId("SITE-1"))
    energy_state = EnergyState.from_telemetry(telemetry, any_asset_offline=False)

    result = graph.invoke({"energy_state": energy_state, "available_forecasts": {}})

    recommendation = result["recommendation"]
    assert any("forecast unavailable" in e for e in recommendation.evidence)
