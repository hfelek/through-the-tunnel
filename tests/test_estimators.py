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
    entries = list_estimators()
    assert {"id": "dummy", "label": "Dummy", "params": {}, "param_info": {}, "constraints": {}} in entries
    for e in entries:  # the UI shows these instead of the code names (T7.9-CR1)
        for name in e["params"]:
            info = e["param_info"].get(name, {})
            assert info.get("label") and info.get("description"), f"{e['id']}.{name} needs a label and a description"
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
