import pytest

from solarops.shared_kernel import AssetId, AssetOperatingMode, AssetType, SiteId
from solarops.telemetry.domain.asset import Asset

BATTERY_ID = AssetId("ASSET-battery-1")
SITE_ID = SiteId("SITE-1")


def test_asset_defaults_to_normal_operating_mode():
    asset = Asset(asset_id=BATTERY_ID, site_id=SITE_ID, asset_type=AssetType.BATTERY)
    assert asset.operating_mode is AssetOperatingMode.NORMAL
    assert asset.config == {}


def test_asset_is_immutable():
    asset = Asset(asset_id=BATTERY_ID, site_id=SITE_ID, asset_type=AssetType.BATTERY)
    with pytest.raises(Exception):
        asset.operating_mode = AssetOperatingMode.MAINTENANCE  # type: ignore[misc]
