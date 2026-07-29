from datetime import UTC, datetime

import pytest

from solarops.decision.application.engine_shells import (
    ConstraintOptimiser,
    MpcOptimiser,
    RlOptimiser,
)
from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.shared_kernel import Power, SiteId, StateOfCharge, Temperature
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_context() -> DecisionContext:
    state = EnergyState.from_telemetry(
        make_telemetry(site_id=SiteId("SITE-1"), timestamp=NOW), any_asset_offline=False
    )
    constraints = OperatingConstraints(
        max_battery_soc=StateOfCharge(95.0),
        min_battery_soc=StateOfCharge(10.0),
        battery_max_temp=Temperature(45.0),
        battery_max_charge_power=Power(50.0),
        battery_max_discharge_power=Power(50.0),
        maintenance_mode=False,
        max_shed_fraction=0.3,
    )
    return DecisionContext(energy_state=state, operating_constraints=constraints)


@pytest.mark.parametrize("engine_cls", [ConstraintOptimiser, MpcOptimiser, RlOptimiser])
def test_shell_raises_not_implemented(engine_cls):
    engine = engine_cls()
    with pytest.raises(NotImplementedError):
        engine.recommend(make_context())


def test_shells_carry_distinct_identity():
    assert ConstraintOptimiser().name == "constraint-optimiser"
    assert MpcOptimiser().name == "mpc-optimiser"
    assert RlOptimiser().name == "rl-optimiser"
