# Through the Tunnel — Implementation Plan

## How to use

Give Claude Code one phase per session, one task at a time (for example: "Implement T2.1 from PLAN.md"). `CLAUDE.md` reminds Claude Code of the rules below in every session.

The plan avoids rework in two ways. First, data formats and interfaces (Section 3) are fixed before any code is written. Second, the system first runs end to end in its simplest form (simulation → baseline estimate → API → screen); advanced methods are plugged into the existing interface later and appear in the UI automatically.

**Working rules**

1. One task = one commit. The commit message starts with the task ID (`T2.1: road geometry`). Do not move on until the task's acceptance criteria are met.
2. Each task has 1–3 light smoke tests; no exhaustive test suites. If `pytest` is not green, the task is not done.
3. The contracts in Section 3 are fixed. If a task needs to change one, Claude Code stops and asks. If approved: `docs/CONTRACTS.md` first, then code, then the user adds a row to the Change log.
4. Change requests that come up mid-way become new tasks in the relevant phase with a `CR` number (for example `T5.3-CR1`). Finished task code is not rewritten; the new task builds on top of it.
5. Every assumption goes into `docs/ASSUMPTIONS.md` with a number (A1, A2…) and is referenced in code where it applies (`# A7`).
6. AI usage: Claude Code ends each task reply with one `AI log:` line; the full log is kept outside the repo and added at delivery (T11.3).
7. The user ticks the task's checkbox when it is done.

**Phase order and why**

| Phase | Content | What you have when it is done |
| --- | --- | --- |
| 0 | Repo setup | Empty but working skeleton |
| 1 | Contracts | Tested JSON schemas and interfaces |
| 2 | Road geometry and true motion | The car's true journey |
| 3 | Sensor models | The data the phone would record |
| 4 | Simulation runner and scenarios | Scenario → trace from the CLI |
| 5 | Baseline estimator and metrics | First error numbers |
| 6 | API | Simulation callable from the browser |
| 7 | Frontend | Simulator working end to end |
| 8 | Advanced estimators | EKF, ZUPT, particle filter, beacons |
| 9 | Monte Carlo and parameter sweeps | Write-up figures |
| 10 | Real data | Validation with phone recordings (optional, nothing depends on it) |
| 11 | Delivery | README, write-up, video, demo rehearsal |

**Division of work: where each task is done**

Code is written in Claude Code; thinking, design and writing happen in Claude.ai. Work in Claude.ai does not use Claude Code credit, so each Claude Code session focuses on one task with ready inputs.

| Where | Tasks | Note |
| --- | --- | --- |
| Claude.ai | T0.2, T0.3 | Rules and doc files; T0.2 is ready |
| Claude.ai | T3.1 | Preset JSON content and sources; Claude Code adds schema validation at the start of T3.2 |
| Claude.ai | T4.2 | Scenario JSON content; Claude Code only runs the validation test |
| Claude.ai | Before T8.2 and T8.4 | Short design note with equations and parameters; Claude Code implements it |
| Claude.ai | T11.1, T11.2, T11.3 | README, write-up, AI usage note |
| User | T10.1 recording, T11.4 | Phone recording, screen recording, demo rehearsal |
| Claude Code | All other tasks | One session = one task |

**Credit rules** (details in `CLAUDE.md`)

- `/clear` before each new task, `/compact` in the middle of a long one.
- Default model: Sonnet. Opus only if stuck in T8.x.
- For tasks touching 3 or more files, Claude Code writes a short plan first and waits for "ok".
- If the same error survives two attempts, end the session.
- Each task is its own commit, so a task that goes wrong is undone with one `git revert`.

## Architecture and stack

Decision: computation in Python, visualization in React (plain JavaScript, no TypeScript), and JSON for everything in between. Simulation, estimators and metrics live in one Python package; both the UI and Monte Carlo call the same code, so two implementations can never drift apart.

```
Scenario JSON ──→ Simulation engine ──┐
                                      ├──→ Trace JSON ──────→ Runner ─────────→ Estimators
Sensor Logger ──→ Data loader ────────┘    (truth +           (measurements          │
                                           measurements)       only)                 │
                                               │ truth only                          │
                                               ▼                                     │
React UI ←── FastAPI ←─────────────────── Metrics ←─────────────────────────────────┘
                                               │
                                               ▼
                                         Monte Carlo ──→ Write-up figures
```

Measurements reach the estimators only through the runner; truth reaches only the metrics layer. Because real recordings are converted to the same trace format, everything downstream runs unchanged.

| Layer | Technology | Why |
| --- | --- | --- |
| Simulation, filters, metrics | Python 3.11+, NumPy, SciPy | Filters and Monte Carlo are quick to write and easy to read |
| Tests | pytest | Each task's acceptance criteria are written as tests |
| Schema validation | Pydantic v2 | Clear error messages for an invalid scenario JSON |
| API | FastAPI + uvicorn | Natural fit with Pydantic, automatic API page at `/docs` |
| Write-up figures | matplotlib | Monte Carlo results as PNGs under `docs/figures/` |
| Frontend | React + Vite, JavaScript | Known stack, smooth live demo |
| Web charts | Recharts | Simple, React-friendly |
| Road and car drawing | SVG (React component) | Easy zoom, tooltips and uncertainty bars |
| Scenario editing | JSON editor panel | A new scenario live = changing a few fields |

**Folder structure**

```
through-the-tunnel/
├── PLAN.md, CLAUDE.md, README.md
├── .claude/settings.json  # blocks reading heavy folders
├── docs/
│   ├── CONTRACTS.md      # copy of Section 3, single source of truth
│   ├── ASSUMPTIONS.md    # A1, A2, ...
│   ├── AI_LOG.md
│   ├── WRITEUP.md
│   └── figures/
├── scenarios/            # scenario JSON files
├── presets/              # sensor noise presets (JSON)
├── data/real/            # raw and converted real recordings
├── sim/                  # Python package
│   ├── contracts/        # Pydantic models, interfaces
│   ├── world/            # road geometry, vehicle motion
│   ├── sensors/          # imu, gnss, baro, mag, ble
│   ├── estimators/       # baseline, ekf, zupt, pf, beacon
│   ├── eval/             # metrics, callout logic, monte carlo
│   ├── realdata/         # Sensor Logger loader
│   ├── api/              # FastAPI
│   └── cli.py
├── tests/
└── web/                  # React + Vite
```

The most important design rule: **estimators never see the true position (truth).** The runner gives them only measurements and the map. So when a real phone recording is converted to the same format, the same estimators run without any change.

## Contracts (fixed)

The formats in this section are turned into code in Phase 1 and afterwards change only through an entry in the Change log. `docs/CONTRACTS.md` is the authoritative copy.

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

Rules: a real recording has no `truth` or only partial truth; a missing sensor field is simply not written. If there is no GNSS fix at a second, that row does not exist (instead of writing an empty value). `mode` values: `gnss`, `dead_reckoning`, `recovering`. The API can decimate the IMU, barometer, magnetometer and truth in the returned trace for the UI with the `decimate_hz` parameter; computation always runs at full rate. `h_acc` is the radial 68% horizontal accuracy in metres, as reported by Android and iOS.

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

## Task list

47 tasks in 12 phases. Each task builds on the previous one; none requires rewriting the code of a finished task. A task is not closed until its "Accept" line is met. Tasks tagged [claude.ai] are done outside Claude Code.

### Phase 0 — Setup

- [ ] **T0.1 Repo skeleton.** Folder structure from Section 2, `pyproject.toml` (numpy, scipy, pydantic, fastapi, uvicorn, matplotlib, pytest, ruff), Vite React JavaScript template under `web/`, `make dev` that starts both services, `GET /api/health`, `.gitignore` (including `out/`, `data/real/raw/`, `node_modules/`).
    - Accept: `pytest` runs; after `make dev` the page opens in the browser and the health call returns "ok".
- [x] **T0.2 CLAUDE.md [claude.ai].** Rules from Section 1, units and frames from Section 3.1, and these prohibitions: estimator code cannot import truth; contracts do not change without asking; no noise parameter without a source.
    - Accept: file is in the repo.
- [ ] **T0.3 Doc files [claude.ai].** `docs/CONTRACTS.md` (copy of Section 3), `docs/AI_LOG.md` template, `docs/ASSUMPTIONS.md` with this initial list:
    - A1 Tunnel is single-lane, no overtaking; the vehicle's route is known from navigation.
    - A2 Map centerline, curvature and grade are accurate (error < 2 m).
    - A3 Phone is fixed in a mount; taking it out of the mount is modeled as a separate scenario.
    - A4 There are at least 60 s of good GNSS before the tunnel (calibration window).
    - A5 Sensors: accelerometer, gyroscope, magnetometer, barometer, GNSS. No vehicle speed data (OBD, CarPlay); discussed as "what if" in the write-up.
    - A6 No GNSS, cellular or Wi-Fi positioning inside the tunnel.
    - A7 Beacons exist only in scenarios that explicitly enable them.
    - A8 In simulation, sensor timestamps are synchronized and delay-free.
    - A9 The callout point is where the exit on the route begins; the driver does not miss the exit.
    - A10 With several vehicles, the single lane means a follower cannot get closer than a minimum gap to the vehicle ahead.
    - Accept: the three files are in the repo.

### Phase 1 — Contracts

- [ ] **T1.1 Scenario model.** Pydantic models for Section 3.2 in `sim/contracts/scenario.py` and the example scenario `scenarios/curved_3km_exit_inside.json`.
    - Accept: the example validates; scenarios with a tunnel beyond the road, an exit off the road or an unknown profile type are rejected with a clear error message (one test each).
- [ ] **T1.2 Trace model.** Models for Section 3.3, JSON write and read, a `decimate(trace, hz)` helper.
    - Accept: write-read round trip returns the same data; decimation only affects IMU, pressure and magnetometer.
- [ ] **T1.3 Estimator interface and registry.** `Estimator`, `Measurement`, `Estimate` types, a `register` decorator, `list_estimators()`.
    - Accept: a dummy method can be registered and appears in the list; it is removed after the test.

### Phase 2 — Road geometry and true motion

- [ ] **T2.1 Road geometry.** Centerline from segments at 1 m resolution: x, y, z, heading, curvature, grade. `RoadMap` class: `at(s)` interpolation, `project(x, y) → s` map matching, `in_tunnel(s)`.
    - Accept: total length equals the sum of segments; heading changes by 90° after a 90° arc; `project(at(s)) == s` (±0.5 m); at 3% grade z = 30 m after 1000 m.
- [ ] **T2.2 Vehicle motion.** `s(t), v(t), a(t)` from the profile list; jerk-limited transitions; seeded slow random speed variation for `speed_jitter_kmh`; `stop_and_go` generator. Then for the vehicle body: yaw, yaw rate, pitch and acceleration in the vehicle frame (longitudinal, lateral = v²·curvature, vertical).
    - Accept: v is never negative; `stop` stops exactly at the target position and waits `dwell_s`; same seed gives the same result; lateral acceleration matches v²/R in curves.
- [ ] **T2.3 Multiple vehicles.** Vehicles are generated in order; a follower cannot get closer than a minimum gap (default 15 m) to the vehicle ahead and slows down if needed (A10).
    - Accept: in a three-vehicle test the gap never drops below the limit.

### Phase 3 — Sensor models

- [ ] **T3.1 Sensor presets [claude.ai].** `presets/flagship_2024.json` and `presets/budget.json`, with a `source` field for each parameter (datasheet or literature; updated with measured values if T10.1 is done). Parameters: accelerometer and gyroscope noise density, initial bias range, bias random walk, scale error; barometer noise and drift; GNSS position and speed noise; magnetometer noise.
    - Accept: presets match the schema; no empty `source`.
- [ ] **T3.2 IMU model.** Starts by adding the preset Pydantic model and its validation test. Gravity is added to vehicle acceleration (specific force) and rotated into the phone frame with the mount rotation; on top: constant bias, bias random walk, white noise and speed-dependent road vibration (only engine idle vibration when stopped). During `handling_events` the mount angle changes and hand-motion noise is added.
    - Accept: at rest on a flat road the acceleration norm ≈ 9.81; in curves the gyroscope's vertical component matches v·curvature; in noise-free mode the inverse transform returns the true acceleration.
- [ ] **T3.3 GNSS model.** 1 Hz position (time-correlated noise), speed, course, `h_acc`. Error grows within `portal_degrade_m` of the tunnel portal; no fixes inside the tunnel; at exit a delay within `reacquire_delay_s`, then `bad_fixes_after_exit` bad fixes.
    - Accept: zero rows inside the tunnel; open-sky error distribution matches the preset; first fixes after exit have the specified error.
- [ ] **T3.4 Barometer model.** Pressure from altitude via the standard atmosphere; noise, slow drift; a `pressure_step_pa` jump at tunnel entry and fan-driven fluctuation.
    - Accept: a 10 m climb gives about 1.2 hPa drop; with tunnel effects off only noise remains.
- [ ] **T3.5 Magnetometer model.** Earth magnetic field (approximate value for Istanbul, with source), position-dependent disturbance of `mag_disturbance_ut` inside the tunnel. Purpose: to show why it is not used.
    - Accept: heading error derived from the magnetometer is clearly visible inside the tunnel.
- [ ] **T3.6 BLE beacon model.** Beacons every `spacing_m`, log-distance path loss + noise, detection threshold, sampling rate.
    - Accept: RSSI peak coincides with passing the beacon (±1 s).

### Phase 4 — Simulation runner and scenarios

- [ ] **T4.1 Runner and CLI.** `run_scenario(scenario, estimators=[]) → trace`; feeds estimators only with measurements as in Section 3.4. `python -m sim run scenarios/x.json -o out.json`.
    - Accept: the same seed gives a byte-identical trace; a 5 km scenario with one vehicle runs in under 5 seconds (without estimators).
- [ ] **T4.2 Scenario library [claude.ai].** Under `scenarios/`: `short_straight_500m`, `curved_2km`, `curved_5km_exit_inside`, `undersea_3km_dip` (−4% down, +4% up), `stop_and_go_3km`, `hard_brake_inside`, `phone_handled_mid_tunnel`, `budget_phone_5km`, `twin_tunnels_short_gap` (200 m between two tunnels), `beacons_5km`.
    - Accept: all validate and run without errors; each `description` says what it tests.

### Phase 5 — Baseline and metrics

- [ ] **T5.1 Baseline method.** Projects GNSS fixes onto the map while available; when GNSS drops, advances `s` with the last reliable speed. Uncertainty grows linearly with time (parameter).
    - Accept: in a constant-speed scenario the error at tunnel exit is < 20 m; in `stop_and_go_3km` the error is large (expected failure, documented in the test).
- [ ] **T5.2 Metrics.** Metrics from Section 3.5 in `sim/eval/metrics.py`, written into the trace.
    - Accept: unit tests with small hand-computed synthetic examples.
- [ ] **T5.3 Callout logic.** For each exit: 500 m, 200 m and "now" callouts; trigger `ŝ + k·σ ≥ exit_s − d` (k default 1, parameter). Actual and ideal callout times are recorded.
    - Accept: with a perfect estimate timing error ≈ 0; larger k shifts callouts earlier.

### Phase 6 — API

- [ ] **T6.1 FastAPI endpoints.** Endpoints from Section 3.6 (except Monte Carlo and real data, which come in T9.3 and T10.5). An invalid scenario returns 422 with a message naming the field. CORS only for the local dev address.
    - Accept: a scenario can be run from the `/docs` page and a trace returned; API tests with `TestClient`.

### Phase 7 — Frontend (the simulator works end to end after this phase)

- [ ] **T7.1 App skeleton.** API client, global state (`useReducer`), scenario picker, "Run" button, loading and error display. Layout: map on top, timeline in the middle, charts below, panel on the right.
    - Accept: picking and running a scenario puts the trace into state; errors show the API message.
- [ ] **T7.2 Top-down map view (SVG).** Road, darker tunnel section, exit markers; true vehicle (filled) and each method's estimate (hollow, method-specific color); ±2σ as a bar along the road. Zoom, pan, "follow the car".
    - Accept: correct positions for each t.
- [ ] **T7.3 Side elevation profile.** s–z chart, tunnel shaded, vehicle positions.
    - Accept: the dip is clearly visible in `undersea_3km_dip`.
- [ ] **T7.4 Playback controls.** Play/pause, speed (×1, ×5, ×20), time slider; all views synced to the same `t`.
    - Accept: dragging the slider moves map and charts together without stutter.
- [ ] **T7.5 Sensor charts.** Longitudinal acceleration (raw and aligned), gyroscope vertical axis, pressure, GNSS `h_acc` and an availability band, BLE RSSI. Tunnel interval shaded, vertical time cursor.
    - Accept: every chart is smooth with `decimate_hz`; the GNSS gap in the tunnel is obvious.
- [ ] **T7.6 Error chart.** Along-track error and ±2σ band per method; ideal and actual callout times marked.
    - Accept: the baseline's failure in `stop_and_go_3km` is visible at a glance.
- [ ] **T7.7 JSON editor and quick sliders.** Scenario JSON in an editable panel; sliders (tunnel length, stop duration, bias multiplier, mount yaw, GNSS reacquire delay) change the JSON directly. The JSON is the single source of truth. "Save as" creates a new scenario file.
    - Accept: a new scenario can be created and run live in under 1 minute.
- [ ] **T7.8 Method picker and metrics table.** Methods come from the API registry, toggle on/off; vehicle × method metrics table.
    - Accept: a newly registered method appears in the list without any frontend change.

### Phase 8 — Advanced estimators

- [ ] **T8.1 Shared preprocessing: alignment.** Gravity direction (low-pass filter), the vehicle's forward axis (matching GNSS speed change with horizontal acceleration), extraction of longitudinal acceleration and vertical-axis yaw rate. Gravity leakage from road grade is corrected with the map grade (3% grade ≈ 0.29 m/s² error). Phone handling is detected and the alignment is marked "invalid".
    - Accept: in a noise-free scenario mount yaw is found within ±1°; a handling event is detected within ±1 s.
- [ ] **T8.2 EKF.** Implements the design note from Claude.ai. State `[s, v, accel_bias]`; prediction with longitudinal acceleration; GNSS update (map projection and speed) with a chi-square gate; weak speed prior (speed limit and last speed).
    - Accept: clearly better than baseline in `hard_brake_inside`; consistency metric in the 85–100% range.
- [ ] **T8.3 Stop detection (ZUPT).** If accelerometer and gyroscope variance in a sliding window is below a threshold, a speed = 0 pseudo-measurement; bias is updated at the same time. False positive rate is reported.
    - Accept: in `stop_and_go_3km` EKF+ZUPT is clearly better than EKF; no false stop detection in constant-speed scenarios.
- [ ] **T8.4 Particle filter + map features.** Implements the design note from Claude.ai. Particles `(s, v, bias)`; weights from: agreement of measured yaw rate with `v·curvature(s)`, agreement of barometric altitude change with `z(s)` (referenced at tunnel entry), GNSS when available. Vectorized with NumPy; 1000 particles by default.
    - Accept: in `curved_5km_exit_inside` and `undersea_3km_dip` the error drops clearly after passing a curve or the dip; in straight, flat tunnels it is no worse than the EKF.
- [ ] **T8.5 Beacon update.** When an RSSI peak is detected, an absolute `s` measurement at the beacon position; pluggable into EKF and PF.
    - Accept: in `beacons_5km` the error stays bounded by the beacon spacing.
- [ ] **T8.6 Tunnel exit and display smoothing.** The chi-square gate rejects the first bad fixes; `display_s` converges to the new estimate within a few seconds and never moves backwards.
    - Accept: maximum display jump drops compared with baseline; `display_s` is monotonically increasing.

### Phase 9 — Monte Carlo and parameter sweeps

- [ ] **T9.1 Monte Carlo runner.** Parallel runs over N seeds (`multiprocessing`); median, 95th percentile and maximum of the metrics; CLI `python -m sim mc scenarios/x.json --runs 300`.
    - Accept: the same seed list gives the same summary.
- [ ] **T9.2 Sweeps and figures.** Tunnel length (0.5, 1, 2, 3, 5 km) × method; bias multiplier × method; stop duration × method. Box plots and heat maps under `docs/figures/`; summary table as CSV.
    - Accept: one command regenerates all figures (`make figures`).
- [ ] **T9.3 Monte Carlo API and UI tab.** `POST /api/montecarlo` (small N, e.g. 50) and a distribution chart in the frontend.
    - Accept: live, after changing a parameter, a 50-run result appears in under 30 seconds.

### Phase 10 — Real data (optional, can be added later)

This phase is optional; no task, including Phase 11, depends on it. Because the trace format (`source: "real"`) and the estimator interface support real data from the start, adding this phase later changes none of the earlier tasks. T10.1 needs only the user's own phone; T10.2–T10.5 happen only if a tunnel recording arrives.

- [ ] **T10.1 Static noise analysis.** Recording with a phone lying on a table (Section 5); noise density, bias and Allan deviation; presets are updated with the measured values and their `source` becomes "measured".
    - Accept: Allan deviation plot under `docs/figures/`.
- [ ] **T10.2 Sensor Logger loader.** Zip or folder → trace: time alignment, iOS → Android axis and unit conversion, lat/lon → local ENU, separating the phone's own "estimated" positions with an `h_acc` threshold, importing annotations into `events`.
    - Accept: a sample recording loads and matches the trace schema.
- [ ] **T10.3 Real tunnel map.** Centerline JSON for the recorded tunnel (from OSM and the GNSS track before/after the tunnel), tunnel length with source.
    - Accept: GNSS points at the tunnel entrance and exit sit within 10 m of the map.
- [ ] **T10.4 Evaluation on real data.** All methods on the real trace; since there is no truth inside the tunnel, the criteria are: difference between the estimated exit time and position and when/where GNSS returns, and annotation times.
    - Accept: a results table and a simulation–reality comparison go into the write-up.
- [ ] **T10.5 Real recording playback in the UI.** `GET /api/real` endpoints and a source picker in the UI (sim / real).
    - Accept: the real recording plays in the same views; no true vehicle is drawn where there is no truth.

### Phase 11 — Delivery

- [ ] **T11.1 README [claude.ai].** Setup, `make dev`, adding a scenario, adding a method, generating figures.
    - Accept: someone following the README on a clean machine runs the simulator within 10 minutes.
- [ ] **T11.2 Write-up [claude.ai].** Approach, assumptions, what was simulated and how, results, limitations, next steps with real devices. English, 4–6 pages, `docs/WRITEUP.md` and PDF.
    - Accept: every claim rests on a figure or table.
- [ ] **T11.3 AI usage note [claude.ai].** A 5–10 line summary from `AI_LOG.md`; at least three concrete correction examples.
    - Accept: each example references the related commit.
- [ ] **T11.4 Screen recording and demo rehearsal.** The list in Section 6.
    - Accept: every live change scenario has been rehearsed.

## Real data recording (optional)

The project is complete without real data; it can be added later through Phase 10. Two recordings are enough: a static recording on a table (T10.1, no car needed) and a tunnel drive (T10.2–T10.4). The app for both is Sensor Logger (iOS and Android): background recording, per-sensor-group sampling rates, timestamped annotations, zipped CSV and JSON export.

### 5.1 Static recording (no car needed)

1. Sensors: accelerometer, gyroscope, magnetometer, barometer. All at the highest sampling rate; raw and calibrated data together if possible.
2. Phone face up on a vibration-free table, away from fans or washing machines. Record 30–60 minutes without touching it.
3. In a separate short recording, place the phone on each of its six faces in turn, wait 30 s on each and mark the face with an annotation. This gives accelerometer bias and scale error.

### 5.2 Tunnel recording protocol

- Safety: the driver never touches the phone; a passenger does the annotations. Without a passenger, recording starts while parked and stops after parking.
- Tunnel: any road tunnel longer than 1 km; sloped undersea tunnels (like the Eurasia Tunnel) are especially valuable for barometer matching.
- Sensors: Accelerometer, Gravity, Gyroscope, Orientation, Magnetometer, Barometer, Location, Activity, Annotations; camera and microphone off; optional Bluetooth. Highest sampling rates.
- Annotation presets: "Tunnel entry", "Tunnel exit", "Stopped", "Moving", "Phone touched".
- Protocol: phone fixed in the mount (photo of it), start recording stationary and wait 60 s, at least 3 minutes of open-sky driving before and after the tunnel, park and wait 30 s before stopping.
- Deliverables: zipped CSV, phone model and OS, car, tunnel name and direction, date and time, traffic level, mount photo, settings screenshot (Standardisation on/off).

### 5.3 Things to watch in real data

- Some phones keep producing their own estimated position inside the tunnel. These are not real fixes; they are told apart by the rise in `h_acc` and constant speed, and are not treated as GNSS measurements (T10.2).
- iOS and Android axis and unit conventions differ; the loader converts according to the Standardisation setting.
- The Activity sensor's "stationary" label is a second reference for checking the ZUPT detector on real data.

## Delivery and demo rehearsal

| Requested | Where | Task |
| --- | --- | --- |
| Code and README | Public repo, `README.md` | T11.1 |
| Write-up (a few pages) | `docs/WRITEUP.md` and PDF | T11.2 |
| AI usage note | Last section of the write-up, sourced from `docs/AI_LOG.md` | T11.3 |
| Screen recording (optional) | 3–5 minutes, linked in the README | T11.4 |

**Live changes they may ask for (rehearsal list)**

- [ ] Make the tunnel 5 km and move the exit close to the end of the tunnel.
- [ ] Add a 60-second traffic stop inside the tunnel.
- [ ] Triple the accelerometer bias and explain how each method degrades.
- [ ] Have the phone picked up mid-tunnel (handling event).
- [ ] Make GNSS return 10 seconds late at the exit with the first 5 fixes bad.
- [ ] Increase barometer fan noise and show how the particle filter reacts.
- [ ] Turn beacons on/off and change their spacing.
- [ ] Switch to the budget phone preset.
- [ ] Show that in a long straight, flat tunnel the particle filter gains nothing (honest failure).
- [ ] Change an estimator parameter live (EKF process noise, ZUPT threshold, callout factor k).
- [ ] Make a small code change live and run the tests.

**Decisions to be ready to defend**

- Why the problem was reduced to 1D and where that assumption breaks.
- Why an EKF and why a particle filter; their cost and difference.
- Why the magnetometer and vehicle speed data (OBD, CarPlay) were not used.
- Where the noise parameters came from and which ones were measured.
- Real data: how it was evaluated, or how it would be validated with a real device.
- Which of Claude Code's decisions were changed and why (three examples from `AI_LOG.md`).

## Change log

Every change that touches the contracts or the task list goes here, newest first.

| Date | Change | Affected |
| --- | --- | --- |
| 2026-10-19 | Beacon positions are part of the map (RoadMap.beacons, trace map.beacons), like exits | Section 3, T8.5 |
| 2026-10-18 | API decimation also applies to truth (UI needs ~10 Hz; truth was sent at the IMU rate) | Section 3.3, T6.1 |
| 2026-10-18 | convoy_3_cars removed; multi-vehicle scenarios are out of scope (the T2.3 code stays). Traffic is represented by a single vehicle in stop_and_go_3km. The 3-vehicle demo item and the T7.2 "3 vehicles" criterion are removed | T4.2, T7.2, Section 6 |
| 2026-10-18 | Plan translated to English | Whole document |
| 2026-10-18 | Division of work and credit rules added; Claude.ai tasks tagged [claude.ai]; CLAUDE.md prepared | Section 1, T0.2, T0.3, T3.1, T4.2, T11.1–T11.3 |
| 2026-10-18 | Real data process (Section 5, Phase 10) made optional | Sections 1, 3.6, 5, 6, T3.1, Phase 10 |
| 2026-10-18 | Plan created | — |
