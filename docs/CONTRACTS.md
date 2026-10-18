# Contracts

Single source of truth for units, frames, data formats, the estimator interface, metrics and the API. Changes only with the user's approval: update this file first, then the code, then add a row to the PLAN.md change log.

The formats in this section are turned into code in Phase 1 and afterwards change only through an entry in the Change log. This file is the authoritative copy.

### 3.1 Units and coordinate frames

| Topic | Decision |
| --- | --- |
| Units | SI: s, m, m/s, m/s², rad, rad/s. Pressure in hPa, magnetic field in µT. Human-facing JSON fields carry explicit suffixes: `_kmh`, `_deg`, `_pct` |
| Time | `t`: seconds since scenario start (float). In a real recording, first sample = 0 |
| World frame | Local ENU: x east, y north, z up. Origin at the road start |
| Position on road | `s`: arc length along the centerline (m). All error metrics use `s` |
| Vehicle frame | x forward, y left, z up |
| Phone frame | Android convention: x to the right of the screen, y to the top of the screen, z out of the screen. The accelerometer reports specific force: a phone lying face up on a table reads +9.81 on z. iOS conversion happens only in the real-data loader |
| Mount | Vehicle-to-phone rotation: yaw, pitch, roll in degrees, set in the scenario. All angles 0 = phone flat, face up, top pointing forward (phone y = vehicle x, phone x = vehicle right, phone z = vehicle up). Applied as intrinsic rotations in the order yaw (about z), pitch (about the new x), roll (about the new y). Pitch 65° tilts the top up toward the driver |
| Heading | Radians, counter-clockwise from east (ENU); left turns have positive curvature; grade = rise/run. GNSS `course` in the trace uses the same convention; conversion from compass bearing happens only in the real-data loader |

### 3.2 Scenario JSON

A scenario defines the road, tunnels, exits, vehicles, phones and environment effects. An exit is the point where navigation makes its callout; the vehicle's planned route is known from the map.

```json
{
  "schema_version": "1.0",
  "id": "curved_3km_exit_inside",
  "description": "3 km curved tunnel, exit at km 1.7 inside the tunnel",
  "seed": 42,
  "rates_hz": { "imu": 100, "gnss": 1, "baro": 10, "mag": 50, "output": 10 },
  "road": {
    "start_heading_deg": 90,
    "segments": [
      { "type": "straight", "length_m": 2000, "grade_pct": 0 },
      { "type": "arc", "length_m": 500, "radius_m": 800, "turn": "left", "grade_pct": -2 },
      { "type": "straight", "length_m": 1500, "grade_pct": 1.5 },
      { "type": "arc", "length_m": 600, "radius_m": 1200, "turn": "right", "grade_pct": 0 },
      { "type": "straight", "length_m": 2000, "grade_pct": 0 }
    ],
    "tunnels": [ { "id": "T1", "start_s": 2000, "end_s": 5000 } ],
    "exits": [ { "id": "E1", "s": 3700, "name": "Exit A" } ],
    "speed_limits": [ { "from_s": 0, "to_s": 6600, "kmh": 80 } ]
  },
  "vehicles": [
    {
      "id": "car1",
      "start_s": 0,
      "start_t": 0,
      "initial_kmh": 70,
      "speed_jitter_kmh": 2,
      "profile": [
        { "type": "cruise", "kmh": 70, "until_s": 2800 },
        { "type": "stop", "at_s": 3000, "decel_mps2": 1.5, "dwell_s": 30 },
        { "type": "ramp", "to_kmh": 60, "accel_mps2": 1.2 },
        { "type": "cruise", "kmh": 60, "until_s": 6600 }
      ],
      "phone": {
        "preset": "flagship_2024",
        "mount": { "yaw_deg": 4, "pitch_deg": 65, "roll_deg": -2 },
        "handling_events": []
      }
    }
  ],
  "gnss_env": {
    "portal_degrade_m": 60,
    "reacquire_delay_s": [2, 6],
    "bad_fixes_after_exit": 3,
    "bad_fix_error_m": 25
  },
  "tunnel_env": {
    "pressure_step_pa": 20,
    "fan_pressure_noise_pa": 8,
    "mag_disturbance_ut": 25
  },
  "beacons": { "enabled": false, "spacing_m": 400, "tx_power_dbm": -59, "path_loss_exp": 2.2 }
}
```

Profile types: `cruise` (constant speed up to a position), `ramp` (speed change), `stop` (stop at a position and wait), `stop_and_go` (seeded random stop-and-go between `from_s` and `to_s`: `kmh` is the speed while moving, `stop_s` = [min, max] stop duration, `go_s` = [min, max] driving time between stops; both ranges are sampled with the scenario seed; example: `{ "type": "stop_and_go", "from_s": 500, "to_s": 1500, "kmh": 30, "stop_s": [5, 20], "go_s": [10, 40] }`). Transitions are jerk-limited. A `handling_events` item: `{ "t": 150, "duration_s": 4, "new_mount": {...} }`.

`tunnel_env.pressure_step_pa` is positive when the pressure inside the tunnel is higher than outside (the barometer then reads a lower altitude).

### 3.3 Trace format

The simulation output and the real-data loader output share the same format. Arrays are columnar (one list per field), so the JSON stays small and can be fed straight into charts.

```json
{
  "schema_version": "1.0",
  "source": "sim",
  "scenario_id": "curved_3km_exit_inside",
  "map": {
    "s": [], "x": [], "y": [], "z": [], "heading": [], "curvature": [], "grade": [],
    "tunnels": [], "exits": [], "speed_limits": []
  },
  "vehicles": [
    {
      "id": "car1",
      "truth": { "t": [], "s": [], "v": [], "a": [], "x": [], "y": [], "z": [], "yaw": [], "pitch": [] },
      "measurements": {
        "imu":  { "t": [], "ax": [], "ay": [], "az": [], "gx": [], "gy": [], "gz": [] },
        "gnss": { "t": [], "x": [], "y": [], "z": [], "speed": [], "course": [], "h_acc": [], "speed_acc": [] },
        "baro": { "t": [], "p_hpa": [] },
        "mag":  { "t": [], "mx": [], "my": [], "mz": [] },
        "ble":  { "t": [], "beacon_id": [], "rssi": [] }
      },
      "events": [ { "t": 0, "type": "tunnel_enter", "ref": "T1" } ],
      "estimates": {
        "baseline": { "t": [], "s": [], "v": [], "sigma_s": [], "display_s": [], "mode": [] }
      },
      "callouts": { "baseline": [ { "exit": "E1", "distance_m": 200, "t": 0, "t_ideal": 0 } ] },
      "metrics": { "baseline": {} }
    }
  ]
}
```

Rules: a real recording has no `truth` or only partial truth; a missing sensor field is simply not written. If there is no GNSS fix at a second, that row does not exist (instead of writing an empty value). BLE rows come at the fixed 100 ms iBeacon advertising interval, not from `rates_hz`. `mode` values: `gnss`, `dead_reckoning`, `recovering`. The API can decimate the IMU for the UI with the `decimate_hz` parameter; computation always runs at full rate. `h_acc` is the radial 68% horizontal accuracy in metres, as reported by Android and iOS.

### 3.4 Estimator interface

Every method implements the same Python class interface and is added to a registry. The API and the UI read the method list from this registry; adding a new method requires no frontend change.

```python
class Estimator(Protocol):
    id: str        # "baseline", "ekf", "ekf_zupt", "pf_map", "pf_map_ble"
    label: str     # name shown in the UI

    def reset(self, road: RoadMap, params: dict) -> None: ...
    def update(self, m: Measurement) -> None: ...   # m.kind: imu | gnss | baro | mag | ble
    def estimate(self, t: float) -> Estimate: ...   # s, v, sigma_s, sigma_v, mode, extras
```

The runner merges all sensor streams by time, calls `update` in order and samples `estimate` at the `output` rate. This structure guarantees causality: no method can see the future, and none can ever see truth.

### 3.5 Metrics

| Metric | Definition |
| --- | --- |
| Along-track error | `s_estimate − s_true` (m), time series |
| In-tunnel RMSE and maximum | Over the time the vehicle is inside the tunnel |
| Error at tunnel exit | At the moment the true vehicle leaves the tunnel |
| Callout timing error | `t_callout − t_ideal` (s). Negative = early. Distances 500 m, 200 m, "now" |
| Recovery time | Time after GNSS returns until abs(error) < 10 m and stays there |
| Maximum display jump | Largest change of `display_s` in one output step minus true progress |
| Consistency | Percentage of time with abs(error) < 2σ. Ideal ≈ 95% |

Consistency is measured inside tunnels only, because with GNSS every method is trivially consistent. Exit error and recovery time are computed per tunnel. Undefined metrics are omitted from the trace rather than written as null, so a missing key means undefined. Callouts fire when `ŝ + k·σ ≥ exit_s − d`; `callout_k` is a navigation-layer parameter applied equally to all estimators.

### 3.6 API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/scenarios` | Scenario list (id, description) |
| `GET /api/scenarios/{id}` | Scenario JSON |
| `GET /api/estimators` | Methods in the registry |
| `GET /api/presets` | Sensor presets |
| `POST /api/simulate` | Body: `{ scenario, estimators, decimate_hz }` → trace |
| `POST /api/montecarlo` | Body: `{ scenario, estimators, runs }` → metric distributions |
| `GET /api/real` and `GET /api/real/{id}` | Converted real recordings (Phase 10, optional) |
