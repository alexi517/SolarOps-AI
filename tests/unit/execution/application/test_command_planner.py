from datetime import UTC, datetime

from solarops.decision.domain.recommendation import Recommendation
from solarops.execution.application.command_planner import CommandPlanner
from solarops.execution.domain.events import CommandCreated
from solarops.shared_kernel import ActionType, AssetId, FixedClock, RecommendationId, SiteId

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_recommendation(**overrides) -> Recommendation:
    defaults = dict(
        recommendation_id=RecommendationId.generate(),
        site_id=SiteId("SITE-1"),
        action=ActionType.CHARGE_BATTERY,
        params={"power_kw": 30.0},
        confidence=0.9,
        expected_benefit="x",
        reason="y",
        generated_at=NOW,
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


def test_plan_carries_recommendation_fields_into_the_command():
    planner = CommandPlanner(FixedClock(NOW))
    recommendation = make_recommendation()

    command, event = planner.plan(recommendation)

    assert command.site_id == recommendation.site_id
    assert command.recommendation_id == recommendation.recommendation_id
    assert command.action is ActionType.CHARGE_BATTERY
    assert command.params == {"power_kw": 30.0}
    assert isinstance(event, CommandCreated)
    assert event.aggregate_id == str(command.command_id)


def test_idempotency_key_is_derived_from_recommendation_id():
    planner = CommandPlanner(FixedClock(NOW))
    recommendation = make_recommendation()
    command, _event = planner.plan(recommendation)
    assert command.idempotency_key == f"idem-{recommendation.recommendation_id}"


def test_asset_id_follows_the_action_kind_convention():
    planner = CommandPlanner(FixedClock(NOW))

    battery_cmd, _ = planner.plan(make_recommendation(action=ActionType.DISCHARGE_BATTERY))
    assert battery_cmd.asset_id == AssetId("SITE-1-battery")

    shed_cmd, _ = planner.plan(make_recommendation(action=ActionType.SHED_LOAD))
    assert shed_cmd.asset_id == AssetId("SITE-1-building-load")

    grid_cmd, _ = planner.plan(make_recommendation(action=ActionType.IMPORT_FROM_GRID))
    assert grid_cmd.asset_id == AssetId("SITE-1-grid")
