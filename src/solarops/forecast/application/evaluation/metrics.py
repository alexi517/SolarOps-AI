"""Forecast accuracy metrics (Document 6 §4) — pure functions, no numpy dependency needed."""

from __future__ import annotations

__all__ = ["mae", "rmse", "mape", "r_squared"]


def _check_same_length(actuals: list[float], predictions: list[float]) -> None:
    if len(actuals) != len(predictions):
        raise ValueError(
            f"actuals and predictions must be the same length, "
            f"got {len(actuals)} vs {len(predictions)}"
        )


def mae(actuals: list[float], predictions: list[float]) -> float:
    """Mean Absolute Error, in the same units as the inputs."""
    _check_same_length(actuals, predictions)
    if not actuals:
        return 0.0
    return sum(abs(a - p) for a, p in zip(actuals, predictions, strict=True)) / len(actuals)


def rmse(actuals: list[float], predictions: list[float]) -> float:
    """Root Mean Squared Error, in the same units as the inputs."""
    _check_same_length(actuals, predictions)
    if not actuals:
        return 0.0
    mean_squared_error = sum(
        (a - p) ** 2 for a, p in zip(actuals, predictions, strict=True)
    ) / len(actuals)
    return mean_squared_error**0.5


def mape(actuals: list[float], predictions: list[float]) -> float:
    """Mean Absolute Percentage Error, as a percentage.

    Zero-actual points are excluded (undefined).
    """
    _check_same_length(actuals, predictions)
    pairs = [(a, p) for a, p in zip(actuals, predictions, strict=True) if a != 0]
    if not pairs:
        return 0.0
    return 100.0 * sum(abs((a - p) / a) for a, p in pairs) / len(pairs)


def r_squared(actuals: list[float], predictions: list[float]) -> float:
    """Coefficient of determination. 1.0 is a perfect fit; can go negative."""
    _check_same_length(actuals, predictions)
    if len(actuals) < 2:
        return 0.0
    mean_actual = sum(actuals) / len(actuals)
    total_variance = sum((a - mean_actual) ** 2 for a in actuals)
    residual_variance = sum((a - p) ** 2 for a, p in zip(actuals, predictions, strict=True))
    if total_variance == 0:
        return 1.0 if residual_variance == 0 else 0.0
    return 1.0 - residual_variance / total_variance
