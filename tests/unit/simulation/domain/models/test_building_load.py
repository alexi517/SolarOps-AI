from datetime import datetime

from solarops.simulation.domain.models.building_load import BuildingLoadModel


def test_noon_weekday_load_exceeds_midnight_load():
    model = BuildingLoadModel(baseline_kw=20.0, peak_kw=60.0, seed=1)
    midnight_load = model.step(datetime(2026, 7, 27, 0, 0))  # Monday
    noon_load = model.step(datetime(2026, 7, 27, 12, 0))
    assert noon_load > midnight_load


def test_weekend_load_lower_than_weekday_at_same_hour():
    weekday_model = BuildingLoadModel(baseline_kw=20.0, peak_kw=60.0, seed=1)
    weekend_model = BuildingLoadModel(baseline_kw=20.0, peak_kw=60.0, seed=1)
    weekday_load = weekday_model.step(datetime(2026, 7, 27, 13, 0))  # Monday
    weekend_load = weekend_model.step(datetime(2026, 8, 1, 13, 0))  # Saturday
    assert weekend_load < weekday_load


def test_shed_load_reduces_demand():
    model = BuildingLoadModel(baseline_kw=20.0, peak_kw=60.0, seed=1)
    before = model.step(datetime(2026, 7, 27, 13, 0))
    model.shed_load(0.5)
    after = model.step(datetime(2026, 7, 27, 13, 0, 5))
    assert after < before * 0.7


def test_restore_load_returns_to_normal_range():
    model = BuildingLoadModel(baseline_kw=20.0, peak_kw=60.0, seed=1)
    model.shed_load(0.8)
    model.restore_load()
    load = model.step(datetime(2026, 7, 27, 13, 0))
    assert load >= 20.0
