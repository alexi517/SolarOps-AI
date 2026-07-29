from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.infrastructure.detector_registry import InMemoryDetectorRegistry

GRID = frozenset({AnomalyType.GRID_INSTABILITY})


class _FakeDetector:
    def __init__(self, name: str) -> None:
        self.name = name
        self.version = "v1"

    def detect(self, state, history):  # noqa: ANN001
        return []


def test_get_active_is_empty_before_registration():
    registry = InMemoryDetectorRegistry()
    assert registry.get_active() == []
    assert registry.covered_types("d1") == frozenset()
    assert registry.get_metrics_by_type("d1") == {}


def test_register_then_get_active_returns_the_detector():
    registry = InMemoryDetectorRegistry()
    detector = _FakeDetector("d1")
    registry.register(detector, GRID, {AnomalyType.GRID_INSTABILITY: {"recall": 0.95}})

    assert registry.get_active() == [detector]
    assert registry.covered_types("d1") == GRID
    assert registry.get_metrics_by_type("d1") == {AnomalyType.GRID_INSTABILITY: {"recall": 0.95}}


def test_register_replaces_the_previous_detector_of_the_same_name():
    registry = InMemoryDetectorRegistry()
    first = _FakeDetector("d1")
    second = _FakeDetector("d1")
    registry.register(first, GRID, {})
    registry.register(second, GRID, {})

    assert registry.get_active() == [second]


def test_register_can_narrow_or_widen_covered_types_on_re_registration():
    registry = InMemoryDetectorRegistry()
    detector = _FakeDetector("d1")
    both_types = frozenset({AnomalyType.GRID_INSTABILITY, AnomalyType.INVERTER_FAULT})
    registry.register(detector, both_types, {})
    registry.register(detector, GRID, {})

    assert registry.covered_types("d1") == GRID


def test_multiple_different_detectors_are_all_active():
    registry = InMemoryDetectorRegistry()
    registry.register(_FakeDetector("d1"), GRID, {})
    registry.register(_FakeDetector("d2"), GRID, {})

    assert {d.name for d in registry.get_active()} == {"d1", "d2"}
