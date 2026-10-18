from sim.contracts.trace import (
    Baro,
    Gnss,
    Imu,
    Measurements,
    Trace,
    Truth,
    VehicleTrace,
    decimate,
    read_trace,
    write_trace,
)


def _trace() -> Trace:
    n = 100
    t = [i * 0.01 for i in range(n)]
    z = [0.0] * n
    imu = Imu(t=t, ax=z, ay=z, az=[9.81] * n, gx=z, gy=z, gz=z)
    gnss = Gnss(t=[0.0, 1.0], x=[0, 1], y=[0, 0], z=[0, 0], speed=[1, 1], course=[0, 0],
                h_acc=[5, 5], speed_acc=[1, 1])
    baro = Baro(t=t, p_hpa=[1013.0] * n)
    veh = VehicleTrace(id="car1", truth=Truth(t=t, s=t),
                       measurements=Measurements(imu=imu, gnss=gnss, baro=baro))
    return Trace(scenario_id="x", vehicles=[veh])


def test_round_trip(tmp_path):
    tr = _trace()
    p = tmp_path / "t.json"
    write_trace(tr, p)
    assert "null" not in p.read_text()
    assert read_trace(p) == tr


def test_decimate_truth_imu_baro_mag():
    tr = _trace()
    out = decimate(tr, 10)
    m, m0 = out.vehicles[0].measurements, tr.vehicles[0].measurements
    assert len(m.imu.t) == 10 and len(m.baro.p_hpa) == 10
    assert m.mag is None and m.gnss == m0.gnss
    assert len(out.vehicles[0].truth.t) == 10 and len(tr.vehicles[0].truth.t) == 100
    assert len(m0.imu.t) == 100
