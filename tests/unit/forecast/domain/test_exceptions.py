import pytest

from solarops.forecast.domain.exceptions import NoRegisteredModel
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.shared_kernel import DomainError


def test_is_a_domain_error():
    error = NoRegisteredModel(ForecastKind.SOLAR_GENERATION)
    assert isinstance(error, DomainError)
    assert error.kind is ForecastKind.SOLAR_GENERATION


def test_message_names_the_kind():
    with pytest.raises(NoRegisteredModel, match="SOLAR_GENERATION"):
        raise NoRegisteredModel(ForecastKind.SOLAR_GENERATION)
