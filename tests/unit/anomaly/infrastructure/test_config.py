from solarops.anomaly.infrastructure.config import AnomalyConfig


def test_default_targets_match_document_6():
    config = AnomalyConfig()
    assert config.precision_target == 0.90
    assert config.recall_target == 0.90
    assert config.detection_delay_target_seconds == 10.0


def test_targets_are_configurable_not_hardcoded():
    config = AnomalyConfig(precision_target=0.5)
    assert config.precision_target == 0.5
    assert AnomalyConfig().precision_target == 0.90


def test_severity_thresholds_are_configurable():
    config = AnomalyConfig(critical_confidence_threshold=0.7, warning_confidence_threshold=0.4)
    assert config.critical_confidence_threshold == 0.7
    assert config.warning_confidence_threshold == 0.4
