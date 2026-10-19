import ast
import json
from pathlib import Path

from sim.contracts.estimation import Estimate, Measurement
from sim.contracts.scenario import load_scenario
from sim.estimators.registry import register, unregister
from sim.runner import run_scenario

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "curved_3km_exit_inside.json"


def _short():
    return load_scenario(SCENARIO)


def _stable_json(trace):
    """Trace as JSON text without the wall-clock compute time, the only machine-dependent value."""
    data = trace.model_dump(mode="json", exclude_none=True)
    for veh in data["vehicles"]:
        for m in veh["metrics"].values():
            m.pop("compute_us_per_measurement", None)
    return json.dumps(data)


def test_same_seed_is_byte_identical():
    sc = _short()
    ests = {"baseline": {}, "ekf": {}}
    a, b = _stable_json(run_scenario(sc, ests)), _stable_json(run_scenario(sc, ests))
    assert a == b
    assert json.loads(a)["vehicles"][0]["measurements"]["imu"]["t"]
    assert "ekf" in json.loads(a)["vehicles"][0]["estimates"]


def test_estimator_sees_only_measurements_in_time_order():
    log = {"reset": [], "updates": [], "estimates": []}

    @register
    class Spy:
        id, label = "spy_test", "Spy"

        def reset(self, *args, **kw):
            log["reset"].append((args, kw))

        def update(self, m):
            log["updates"].append(m)

        def estimate(self, t):
            log["estimates"].append(t)
            assert all(m.t <= t for m in log["updates"])
            return Estimate(t=t, s=0.0, v=0.0, sigma_s=1.0, sigma_v=1.0, mode="gnss")

    try:
        tr = run_scenario(_short(), {"spy_test": {"k": 1}})
    finally:
        unregister("spy_test")
    (args, kw), = log["reset"]
    assert len(args) == 2 and not kw and args[1] == {"k": 1} and hasattr(args[0], "in_tunnel")
    assert log["updates"] and all(type(m) is Measurement for m in log["updates"])
    t = [m.t for m in log["updates"]]
    assert t == sorted(t)
    assert all("truth" not in m.data and "s" not in m.data for m in log["updates"] if m.kind != "ble")
    est = tr.vehicles[0].estimates["spy_test"]
    assert len(est.t) == len(log["estimates"]) and est.display_s == est.s


def test_changing_gnss_preset_keeps_imu_identical(monkeypatch):
    from sim import runner

    sc = _short()
    base = run_scenario(sc).vehicles[0].measurements
    real = runner.load_preset

    def tweaked(name):
        p = real(name)
        p.gnss.position_corr_time.value *= 2
        return p

    monkeypatch.setattr(runner, "load_preset", tweaked)
    other = run_scenario(sc).vehicles[0].measurements
    assert other.imu == base.imu and other.baro == base.baro and other.mag == base.mag
    assert other.gnss != base.gnss

    # truth isolation: no estimator module imports sensor, eval, runner or vehicle code (parsed, so comments and strings do not count)
    banned = ("sim.sensors", "sim.eval", "sim.runner", "sim.world.vehicle")
    for path in (Path(__file__).resolve().parents[1] / "sim" / "estimators").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imported = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported = [node.module or ""] + [f"{node.module}.{a.name}" for a in node.names]  # "from sim import sensors"
            else:
                continue
            assert not [i for i in imported if any(i == b or i.startswith(b + ".") for b in banned)], f"{path.name} imports {imported}"
