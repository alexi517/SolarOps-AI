import pytest

from solarops.forecast.application.evaluation.metrics import mae, mape, r_squared, rmse


def test_mae_known_answer():
    assert mae([10.0, 20.0, 30.0], [12.0, 18.0, 33.0]) == pytest.approx((2 + 2 + 3) / 3)


def test_mae_empty_is_zero():
    assert mae([], []) == 0.0


def test_rmse_known_answer():
    assert rmse([0.0, 0.0], [3.0, 4.0]) == pytest.approx(((9 + 16) / 2) ** 0.5)


def test_mape_known_answer():
    assert mape([100.0, 200.0], [90.0, 220.0]) == pytest.approx((10.0 + 10.0) / 2)


def test_mape_excludes_zero_actuals():
    assert mape([0.0, 100.0], [5.0, 110.0]) == pytest.approx(10.0)


def test_mape_all_zero_actuals_is_zero():
    assert mape([0.0, 0.0], [1.0, 2.0]) == 0.0


def test_r_squared_perfect_fit_is_one():
    assert r_squared([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_r_squared_constant_actuals_with_perfect_prediction_is_one():
    assert r_squared([5.0, 5.0], [5.0, 5.0]) == 1.0


def test_r_squared_constant_actuals_with_imperfect_prediction_is_zero():
    assert r_squared([5.0, 5.0], [4.0, 6.0]) == 0.0


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError, match="same length"):
        mae([1.0], [1.0, 2.0])
