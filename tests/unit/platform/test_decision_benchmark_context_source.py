from datetime import UTC, datetime

from solarops.decision.application.rule_based_optimiser import RuleBasedOptimiser
from solarops.decision.infrastructure.config import RuleEngineConfig
from solarops.platform.decision_benchmark_context_source import DecisionBenchmarkContextSource
from solarops.shared_kernel import ActionType, FixedClock


def test_scenario_names_returns_all_six():
    source = DecisionBenchmarkContextSource()
    assert len(source.scenario_names()) == 6


def test_context_for_returns_a_usable_decision_context():
    source = DecisionBenchmarkContextSource()
    context = source.context_for("Clear Day")
    assert context.energy_state is not None
    assert context.operating_constraints is not None


def test_battery_overheating_scenario_context_reflects_the_fault():
    source = DecisionBenchmarkContextSource()
    context = source.context_for("Battery Overheating")
    observed = context.energy_state.battery_temp.value
    limit = context.operating_constraints.battery_max_temp.value
    assert observed > limit


def test_engine_produces_a_recommendation_for_every_scenario():
    source = DecisionBenchmarkContextSource()
    clock = FixedClock(datetime(2026, 7, 27, 12, 0, tzinfo=UTC))
    engine = RuleBasedOptimiser(RuleEngineConfig(), clock)
    for scenario_name in source.scenario_names():
        ranked = engine.recommend(source.context_for(scenario_name))
        assert ranked.top.action in ActionType
