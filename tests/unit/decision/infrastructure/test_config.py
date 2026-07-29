from solarops.decision.infrastructure.config import RuleEngineConfig


def test_default_healthy_band_matches_brief_intent():
    config = RuleEngineConfig()
    assert config.battery_healthy_min_soc_pct == 30.0
    assert config.battery_healthy_max_soc_pct == 85.0


def test_thresholds_are_configurable_not_hardcoded():
    config = RuleEngineConfig(battery_healthy_min_soc_pct=40.0)
    assert config.battery_healthy_min_soc_pct == 40.0
    assert RuleEngineConfig().battery_healthy_min_soc_pct == 30.0
