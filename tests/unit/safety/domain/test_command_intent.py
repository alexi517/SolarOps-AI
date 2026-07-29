import pytest

from solarops.safety.domain.command_intent import CommandIntent
from solarops.shared_kernel import ActionType, AssetId, CommandId, SiteId


def test_params_default_to_empty_dict():
    intent = CommandIntent(
        command_id=CommandId.generate(),
        site_id=SiteId("SITE-1"),
        asset_id=AssetId("ASSET-battery-1"),
        action=ActionType.CHARGE_BATTERY,
    )
    assert intent.params == {}


def test_asset_operating_mode_defaults_to_unknown():
    intent = CommandIntent(
        command_id=CommandId.generate(),
        site_id=SiteId("SITE-1"),
        asset_id=AssetId("ASSET-battery-1"),
        action=ActionType.CHARGE_BATTERY,
    )
    assert intent.asset_operating_mode is None


def test_command_intent_is_immutable():
    intent = CommandIntent(
        command_id=CommandId.generate(),
        site_id=SiteId("SITE-1"),
        asset_id=AssetId("ASSET-battery-1"),
        action=ActionType.CHARGE_BATTERY,
    )
    with pytest.raises(Exception):
        intent.action = ActionType.NO_OP  # type: ignore[misc]
