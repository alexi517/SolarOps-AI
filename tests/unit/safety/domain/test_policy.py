import pytest

from solarops.safety.domain.policy import Policy
from solarops.shared_kernel import PolicyId, SiteId, StateOfCharge


def make_policy(**overrides):
    defaults = dict(
        policy_id=PolicyId.generate(),
        site_id=SiteId("SITE-1"),
        version=1,
        max_battery_soc=StateOfCharge(95.0),
        min_battery_soc=StateOfCharge(10.0),
    )
    defaults.update(overrides)
    return Policy(**defaults)


def test_defaults_are_conservative():
    policy = make_policy()
    assert policy.maintenance_mode is False
    assert policy.maintenance_override is False
    assert policy.max_shed_fraction == 0.0


@pytest.mark.parametrize("fraction", [-0.01, 1.01])
def test_max_shed_fraction_must_be_within_zero_and_one(fraction):
    with pytest.raises(ValueError, match="max_shed_fraction"):
        make_policy(max_shed_fraction=fraction)


def test_policy_is_immutable():
    policy = make_policy()
    with pytest.raises(Exception):
        policy.maintenance_mode = True  # type: ignore[misc]
