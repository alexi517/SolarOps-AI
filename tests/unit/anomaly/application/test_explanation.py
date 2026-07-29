import pytest

from solarops.anomaly.application.explanation import recommended_action_for
from solarops.anomaly.domain.anomaly_type import AnomalyType


@pytest.mark.parametrize("anomaly_type", list(AnomalyType))
def test_every_anomaly_type_has_a_recommended_action(anomaly_type):
    action = recommended_action_for(anomaly_type)
    assert isinstance(action, str)
    assert action
