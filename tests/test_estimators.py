import pytest

from sim.contracts.estimation import Estimate, Measurement
from sim.estimators import get_estimator, list_estimators, register, unregister


@pytest.fixture
def dummy():
    @register
    class Dummy:
        id = "dummy"
        label = "Dummy"

        def reset(self, road, params):
            self.t = 0.0

        def update(self, m):
            self.t = m.t

        def estimate(self, t):
            return Estimate(t, 0.0, 0.0, 1.0, 0.1, "dead_reckoning")

    yield Dummy
    unregister("dummy")


def test_register_and_list(dummy):
    assert {"id": "dummy", "label": "Dummy"} in list_estimators()
    assert get_estimator("dummy") is dummy
    with pytest.raises(ValueError):
        register(dummy)


def test_removed_after_test():
    assert all(e["id"] != "dummy" for e in list_estimators())


def test_types_are_slotted(dummy):
    m = Measurement(0.0, "baro", {"p_hpa": 1013.0})
    assert not hasattr(m, "__dict__")
    e = dummy()
    e.update(m)
    assert e.estimate(1.0).mode == "dead_reckoning"
