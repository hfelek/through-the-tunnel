# Code tour

For a reader who knows the concepts (Kalman filters, IMU/GNSS, React) but has not read this code. Line numbers are
`file:line` as of the DOC1 commit; function and class names are the stable anchors, so search for the name if a line has
moved. Every task updates the section of the module it touches (CLAUDE.md, Definition of done).

Conventions used everywhere: SI units (s, m, m/s, m/s², rad, rad/s), pressure in hPa, magnetic field in µT. Position
along the road is the arc length `s` (m). Vehicle frame: x forward, y left, z up. Phone frame: Android (x right, y up
the screen, z out of the screen). Details and the trace format: `docs/CONTRACTS.md`. Numbered assumptions (A1, A2, ...):
`docs/ASSUMPTIONS.md`.

## 1. Overview: the data flow

```
scenarios/*.json ──► sim/contracts/scenario.py   Scenario (validated, extra keys forbidden)
                          │
                          ▼
                     sim/world/road.py           RoadMap (`from_columns` builds one from measured columns, T10.5a): centerline (x, y, z, heading, curvature, grade) per 1 m,
                          │                      at(s), project(x, y), in_tunnel(s)
                          ▼
                     sim/world/vehicle.py        VehicleMotion = TRUTH: t, s, v, a, yaw, yaw_rate, pitch, a_lat, a_vert
                          │
                          ▼
                     sim/sensors/*.py            imu, gnss, baro, mag, ble: truth + presets/*.json + noise → columns
                          │
                          ▼
                     sim/runner.py               run_scenario(): builds the sensors with one seeded rng per sensor,
                          │                      merges them into a time-ordered Measurement list
          ┌───────────────┴────────────────┐
          ▼  (never sees truth)            ▼  (truth side)
   sim/estimators/*.py                sim/eval/metrics.py, callouts.py
   update(m) → estimate(t)            error vs truth, RMSE, consistency, exit error, callout timing
          └───────────────┬────────────────┘
                          ▼
                     Trace (sim/contracts/trace.py): truth + measurements + estimates + callouts + metrics
                          │
                          ▼
                     sim/api/main.py             FastAPI: /api/scenarios, /api/simulate, ...
                          │
                          ▼
                     web/src/                    React: state.js (reducer) → components; the scenario JSON in state
                                                 is the single source of truth, every control edits it
```

Who calls whom: `web/src/App.jsx` calls `POST /api/simulate` (`web/src/api.js:37`), which calls `run_scenario`
(`sim/api/main.py:94`, `sim/runner.py:127`). Determinism: one `SeedSequence(scenario.seed)` is spawned into a motion rng
and one rng per sensor (`sim/runner.py:134-138`), so changing one sensor's preset never changes another sensor's noise
(tested in `tests/test_runner.py`).

## 2. `sim/contracts`: the data shapes

Purpose: Pydantic models (validated, serializable) for the scenario, the presets, the trace, and plain dataclasses for what
an estimator sees. Nothing here computes anything except validation.

| File | What | Key items |
| --- | --- | --- |
| `scenario.py` | Scenario JSON → `Scenario` | `_Model` forbids unknown keys (`:10`, `extra="forbid"`, so a typo is an error); `Road._on_road` (`:76`) rejects tunnels/exits/limits off the road; `_check_plan` (`:188`: plan sorted, on the road, room to brake); `Scenario._vehicles_on_road` (`:236`); `load_scenario` (`:245`) |
| `preset.py` | `presets/*.json` → `Preset` | every physical value is a `Param` with `value`, `unit`, `source` (`:12`); `load_preset` (`:53`) |
| `trace.py` | The output format, columnar (one list per field) | `VehicleTrace` (`:106`) holds `truth`, `measurements`, `events`, `estimates`, `callouts`, `metrics`; `decimate` (`:146`) thins truth/imu/baro/mag for the UI |
| `estimation.py` | What estimators see | `Measurement(t, kind, data)` (`:15`), `Estimate(t, s, v, sigma_s, sigma_v, mode)` (`:24`), the `Estimator` protocol (`:34`: `reset`, `update`, `estimate`) |

Inputs/outputs: scenario JSON in metres, seconds, km/h (fields named `_kmh`, `_deg`, `_pct` are human-facing); the trace
uses SI. Missing sensors are absent fields, never nulls.

A-numbers: A3 (mount), A4 (60 s of GNSS before a tunnel), A8 (no timestamp error) are scenario-level conventions.

## 3. `sim/world`: road and vehicle (the truth)

### `road.py`: the map

- `build_centerline` (`:24`) integrates the segments exactly: straights and circular arcs, left turn = positive curvature.
  The lines that matter:
  `k = (1.0 if seg.turn == "left" else -1.0) / seg.radius_m` (`:34`) and
  `x = x0 + (np.sin(h) - np.sin(h0)) / k` (`:39`), the closed-form arc.
- `RoadMap.at(s)` (`:82`): x, y, z, heading interpolated; curvature and grade are piecewise constant, taken at the sample
  at or before `s` (`:86-90`).
- `RoadMap.project(x, y)` (`:93`): nearest point on the centerline → `s`. This is how GNSS positions become map positions.
- `RoadMap.beacons` (set by the runner when beacons are enabled): `[(beacon_id, s)]`, map knowledge like `exits` (T8.5).
- `RoadMap.in_tunnel(s)` (`:110`). Estimators may use the whole `RoadMap` (A2: the map is accurate).

### `vehicle.py`: how the car drives

- `simulate_vehicle` (`:164`) walks the scenario's driving `plan` (`speed`, `stop`, `traffic` points, by position, like speed
  signs) at the IMU rate and returns a `VehicleMotion` (`:22`): `t, s, v` (m/s), `a` (m/s²), `yaw, yaw_rate, pitch, a_lat, a_vert`.
- One `_Run` method per plan point: `speed_point` (`:129`), `stop_point` (`:137`), `traffic` (`:142`). A lower speed or a stop
  uses `brake_to` (`:107`): hold the speed, start braking as late as possible so the new speed is reached exactly at `s`
  (distance = mean speed x duration of the S-curve). A higher speed uses `hold_until` (`:102`), then `change`.
- `sim/world/speed_change.py`: `s_curve` (jerk-limited speed change with zero acceleration at both ends, A11, 2 m/s³) and
  `s_curve_distance`; the same functions let the scenario validation (`_check_plan` in `contracts/scenario.py`, `:188`)
  reject a slowdown that is too close to the previous point.
- `_Run.step` (`:64`): the speed at every step is the target speed plus a slow random "driver jitter" (A27, 4 cosines,
  `:52`), capped by the gap to a leading vehicle (A10). The jitter is on only while a speed is held.
- The physics that the IMU later relies on: `yaw_rate=v * pos["curvature"]` and `a_lat=v**2 * pos["curvature"]`
  (in `simulate_vehicle`); pitch follows the grade, blended over 40 m (`_road_pitch`, `:156`, A12).
- `simulate_vehicles` (`:202`): several vehicles in one lane, each following the previous one.

A-numbers: A10, A11, A12, A13, A27.

## 4. `sim/sensors`: truth → measurements

Every generator draws all its random numbers first, so the stream does not depend on options. Each takes the truth
(`VehicleMotion`), the `RoadMap`, the preset (datasheet-sourced values) and its own seeded rng, and returns a dict of
columns with a time array `t`.

### `imu.py` (A17)

- `generate_imu` (`:140`) → `t, ax, ay, az` (m/s², specific force, phone frame), `gx, gy, gz` (rad/s).
- `_vehicle_signals` (`:118`) is the physics: `force = [a + G sinθ, a_lat, a_vert + G cosθ]` (`:122`). The accelerometer
  measures specific force, so a phone lying flat reads +9.81 on z.
- Gyro, `:150-151`: the phone's rotation rate is the vehicle's seen from the phone plus the mount path's own
  (`mount_rate`, `:107`). That is why integrating the gyro over a handling event recovers the mount change.
- `MountPath` (`:81`) and `_EventPath` (`:42`): the phone orientation over time. A handling event (pick-up, hold with
  re-orientations, put-back, hand wobble) is one continuous rotation path. One `MountPath` is shared by the IMU and the
  magnetometer (`sim/runner.py:140`).
- Errors (`:157-162`): `x * scale + bias + white + vib`, plus 2 m/s² hand noise on the accelerometer during handling.

### `gnss.py` (A15, A18, A19)

- `generate_gnss` (`:51`) → `t, x, y, z, speed, course, h_acc, speed_acc`; only times with a fix exist (no rows inside
  tunnels).
- Position error is a first-order Gauss-Markov process per axis (`_gauss_markov`, `:23`, 30 s correlation, A15), grown up
  to 5× near portals (`_portal_factor`, `:15`, A19).
- `_availability` (`:34`): no fix inside, a reacquire delay after exit, then `bad_fixes_after_exit` fixes with a large
  error. `h_acc` honestly reports the larger error (`:71`).

### `baro.py` (A20, A21, A22)

- `generate_baro` (`:48`) → `t, p_hpa`. Pressure from the true altitude by the standard atmosphere (`pressure_hpa`, `:16`)
  plus noise, drift, the tunnel step (`_step_pa`, `:21`) and fan fluctuation (`_fan_pa`, `:38`).

### `mag.py` (A23)

- `generate_mag` (`:27`) → `t, mx, my, mz` (µT): Earth field rotated into the phone frame plus a spatial Gauss-Markov
  disturbance inside tunnels (`_tunnel_field`, `:16`). No estimator uses it; it exists to show why.

### `ble.py` (A24, A25, A26)

- `generate_ble` (`:25`) → `t, beacon_id, rssi` (dBm), every 100 ms per beacon in range. The model is
  `rssi = tx_power - 10 n log10(d) + noise` (`:35`); packets below -90 dBm are dropped. `beacon_positions` (`:14`) is called by the
  runner, which stores the result in `RoadMap.beacons` (and in the trace `map.beacons`) for estimators.

## 5. `sim/geometry`

`so3.py`: `exp_so3` (rotation vector → matrix), `log_so3` (matrix → rotation vector), `skew`, `smooth_step`. Pure numpy, shared
by the sensor models and the estimators so that estimators never import sensor code.

## 6. `sim/estimators`

Estimators see only the map and time-ordered `Measurement`s (see section 11).

### `registry.py`

- `@register` (`:13`) puts a class in `_REGISTRY` by its `id` (`:18`). `list_estimators` (`:38`) returns
  `{id, label, params, constraints}` for the API and the UI; `validate_params` (`:46`) rejects unknown names and out-of-range
  values (a `bool` constraint accepts only true/false); `EstimatorFailed` (`:26`) turns a crash inside an estimator into an API 422.
- A class declares `default_params`, `constraints` (`{"type": "int"|"float", "min"?, "gt"?}`) and `param_info` (`{name: {label, unit, description}}`, T7.9-CR1: what the UI shows instead of the code name; `list_estimators` returns it and `tests/test_estimators.py` requires a label and a description for every parameter); the UI builds its
  parameter inputs from them. Subclasses extend the parent's dict (`{**EkfEstimator.param_info, ...}`).

### `baseline.py`: the baseline

- `update` keeps the last GNSS fix; `estimate` (`:62`) extrapolates with the average of the last speeds:
  `sigma = self._sigma_fix + self.sigma_rate_mps * dt` (`:68`) grows linearly during an outage. No IMU.

### `alignment.py`: the `Aligner` (T8.1)

Turns raw phone IMU samples into the vehicle's longitudinal acceleration and yaw rate, finds the mount from GNSS, and
detects the phone being handled. One per estimator. Design: PLAN T8.1, assumptions A28-A30.

- `process_gnss(m)` (`:143`) closes the previous fix interval (`_close_interval`, `:156`) into a record: integrals of the
  accelerometer, of `v·gyro`, of `v`, and the speed change.
- `_solve` (`:195`) turns the records into the mount: up axis `u` (mean accelerometer on flat road), gyro bias (mean gyro on
  straight, flat road), forward axis from a 2-D Procrustes fit (`_fit`, `:180`):
  `p = np.stack([dv + gr, wv @ u - (b @ u) * vi], axis=1)` (`:188`) is the expected vehicle acceleration (forward, left) per
  interval, `psi = float(np.arctan2(...))` (`:192`) the yaw that rotates it onto the measured one. `sigma_psi` comes from
  the residuals.
- `process_imu(m, s_est, v_est)` (`:327`) returns an `AlignedSample` (`:28`: `a_long`, `sigma_a_long`, `yaw_rate`, `valid`,
  `mode`, `sigma_tilt`, `mount_changed`). The outputs, `:388-389`:
  `a_long = f·a - G·sin(atan(grade(s_est)))` removes the gravity leaking in on a slope; `sigma = hypot(sigma_base,
  sigma_psi·|v·yaw_rate|)`.
- Handling detection (`:341-360`), gyro only, so a hard brake cannot trigger it: the 0.2 s-averaged gyro minus bias minus
  the expected vehicle rotation, `score = norm(w - vk * u)` (`:347`); start above 0.15 rad/s for 0.2 s, end below
  0.03 rad/s for 1 s (A29).
- Re-alignment after put-back (`_end_hand`, `:261`): integrate the gyro over the event, remove the vehicle's own rotation,
  `m1 = d_rv.T @ pre.m @ self._R` (`:276`; derivation in the docstring), then fuse with the gravity tilt
  (`_gravity_step`, `:286`, inverse-variance weights `:319`, A30).
- Calibration samples are only taken when GNSS is current and not near a hand movement (`eligible`, `:363`).
- Output modes: `uncalibrated`, `aligned`, `in_hand`, `realigned`; `valid` is False unless aligned or realigned.

### `ekf.py`: the EKF (T8.2, `docs/design/T8.2_ekf.md`, A31)

`flat_grade` and `straight_curvature` (T10.5a) are passed to the `Aligner` in `reset`; the defaults equal the Aligner's, so simulation runs are unchanged. The real recording uses 0.03 and 2e-3.

State `[s, v, b, d_psi]`: position, speed, acceleration offset, remaining mount yaw error (a consider state).

- Parameters and constraints: `:27-37`. `reset` (`:40`) creates one `Aligner`.
- `_imu` (`:105`): passes its own position and speed to the aligner so grade leakage is removed at the EKF's position
  (`:106`), inflates `P_bb` on a new mount (`:111`), then predicts. Aligned prediction (`:127`):
  `acc = a.a_long - b - d * v * w` (acceleration minus offset minus the yaw error's share). Process noise uses only
  `sigma_base`; the yaw error is in `d_psi`, not counted twice.
- Trust rule (`:125`): `if a.valid and (gnss_current or sqrt(P_bb) <= accel_trust_sigma_b)`: with a poorly known offset and
  no GNSS, the constant-velocity branch is used instead.
- `_kalman` (`:76`): generic update, chi-square gate (`:80`), Joseph form, and
  `k[3, :] = 0.0` (`:83`): `d_psi` is a consider state, its mean is never updated.
- `_gnss` (`:200`): map-match the fix, reject if its lateral distance is over `lateral_k` sigma (`:208`), update with
  position and speed.
- Weak speed prior (`:148`): pull `v` down if it is above `speed_limit_factor` × the limit.
- `estimate` (`:227`) returns `s, v, sqrt(P)` and the mode (`gnss`, `recovering`, `dead_reckoning`).
- `EkfZuptEstimator` (`:274`, id `ekf_zupt`, label "EKF + ZUPT"): the same class with `zupt = True` and five more parameters
  (`zupt_acc_std`, `zupt_gyro_std`, `zupt_v_sigma`, `zupt_gate_chi2`, `zupt_bias_floor_mps2`). `ekf` stays without ZUPT so the two can be compared.
  `_stationary_updates` (`:187`), called at the end of `_imu`: while the detector says stationary, `v = 0` every 0.1 s through
  `_kalman(..., gate=zupt_gate_chi2, keep_s=False)` (a rejected update is counted in `zupt_gated`; T9.3: `keep_s=False` sets the s gain to 0, because the detector can fire while the car still creeps and P_sv/P_vv of ~22 s would turn the false `v = 0` into metres), and once per second the mean aligned
  `a_long` as a measurement of `b` (`H = [0, 0, 1, 0]`, true acceleration is 0) with `R = max(s_win, 0.02)^2 / n + zupt_bias_floor_mps2^2` (`s_win` = std of `a_long` in the window; T9.3, A28/A32), gated at chi-square 10.8 (`BIAS_GATE_CHI2`; a rejected window is counted in `bias_gated`). `_speed_not_zero` (`:183`) is the same
  chi-square test; a bias window that fails it is dropped, because the detector lags the departure by about 2 s and the
  window would hold real acceleration (A32).
- Exit safeguard (T8.6): in `_gnss` (`:212`), a fix that passes the lateral check but fails the gate adds to `_gate_streak`;
  at `gate_reset_n` (5) `_reinit_from_fix` (`:174`) takes `s` and `v` from the fix (keeps `b`, `d_psi`) and counts `gate_resets`.
- Display smoothing (T8.6): `_advance_display` (`:165`), called every IMU step, moves `display_s` at
  `clip(v + display_k * (s - display_s), 0, v + display_max_catchup)`; `estimate` passes it in `extras["display_s"]`
  and the runner writes it to the `display_s` column (callouts still use `s`).
- Beacon update (T8.5, A33): `_ble` (`:239`) feeds each packet of a beacon the map knows (`road.beacons`) to that beacon's
  `PeakDetector` (`beacon_peak.py`); `_beacon_silence` (`:248`), called every IMU step, ends a pass after 1 s of silence.
  `_beacon_update` (`:255`): `z = s_b + v * (t_det - t_peak)`, variance `beacon_sigma^2 + (age * sigma_v)^2`, `H = [1, 0, 0, 0]`,
  1-dof gate; it never touches `_gate_streak`. `beacon_updates` counts accepted updates. Without beacons `road.beacons` is empty.

### `beacon_peak.py`: the beacon pass detector (T8.5, A33)

- `PeakDetector` (one per beacon): `add(t, rssi)` keeps a 1 s moving average; once it passes `min_dbm` it records the smoothed
  values and reports a pass when the value drops `drop_db` below its maximum. `poll(t)` reports a pass after 1 s without
  packets. `_finish` returns the time of the maximum, or the middle of the plateau (within 1 dB of the maximum for more than
  3 s) when the car stopped next to the beacon. After a pass it stays disarmed until the average falls below `min_dbm`.
  T9.3: `_finish` returns that time minus `SMOOTH_S / 2`, the group delay of the causal moving average (measured +0.50 s, about 10 m
  at 20 m/s, T9.2). The EKF's `beacon_sigma` default is 10 m, the per-pass spread measured then (9.9 m).

### `pf.py`: the particle filter (T8.4, `docs/design/T8.4_pf.md`, A34)

- `PfEstimator` (`:30`, id `pf`) wraps an `EkfZuptEstimator` (`self.ekf`): `update` passes every measurement to the EKF first.
  The EKF stores its aligned sample in `ekf.aligned` (one line in `_imu`) so the PF can read the yaw rate.
- Particles are `s`, `dv` (speed offset from the EKF speed) and weights `w`. `_redraw` (`:73`) re-samples them from the EKF's
  belief whenever the EKF accepted a GNSS fix or a beacon update (detected by a change of `ekf._t_acc` / `beacon_updates`).
- Map matching runs only in the tunnel (`_in_tunnel`, `:65`: first fix done, EKF mode `dead_reckoning`). `_step` (`:104`) every
  0.1 s: `_propagate` (`:121`) moves `s` by `(v_ekf + dv) * dt` and sums each particle's expected yaw rate `v * curvature(s)`;
  every 1 s `_weigh` (`:132`) first measures the spread of the particles' expected yaw rates; below `informative_ratio * sigma_yaw`
  (e.g. a straight road) it does nothing (CR3; the recentring tried in CR3 was removed in CR4). CR6: `_propagate` runs at every step, also while GNSS is current (before, the cloud stood still for the 1.5 s `gnss_timeout_s` after the last fix and started ~33 m behind on straight tunnels); weighting is tunnel-only); otherwise
  `_weigh_and_resample` (`:142`) multiplies the weights by the curvature likelihood and resamples when
  N_eff < N/2 (`systematic_resample`, `:22`, plus jitter). CR2: there is no barometer matching (A34); the barometer stays a sensor
  and a chart only.
- CR1: `_propagate` also adds `N(0, sqrt(max(0, ΔP_vv)))` to every `dv` (`_pvv_prev`); The `bool` constraint type (registry, `EstimatorPicker` checkbox) stays, although no estimator has a bool parameter now.
- `estimate` (`:162`): in the tunnel the weighted mean and std of `s`, `v_ekf` + weighted mean `dv`; otherwise the EKF's.
  `display_s` is the T8.6 rule applied to the particle mean (`_advance_display`, `:155`).
- Recipe, a new PF parameter: add it to `_OWN` (`:16`), to `param_info` and, if it needs a constraint, to `constraints`; unknown names go to the EKF.

### `stationary.py`: the stationary detector (T8.3, A32)

`StationaryDetector.update(t, ax, ay, az, gx, gy, gz)` returns True while the std of `|accelerometer|` and `|gyro|` over the
last 1.0 s stay below the two limits for 0.5 s (`:27-48`). It uses magnitudes, so it needs no mount alignment, and it keeps
running sums, so a sample costs O(1). Hand motion and driving vibration keep the std high (A17). It is not a registered
estimator; the EKF owns one instance.

## 7. `sim/eval`: the truth side

- `metrics.py: compute_metrics` (`:34`): `err = es - s_true` (`:46`), in-tunnel RMSE and max, exit error, recovery time
  (`_recovery_s`, `:22`), max display jump, consistency `100·mean(|err| < 2σ)` inside tunnels (`:55`), callout timing.
  Undefined metrics are omitted (no truth, no samples, never recovered).
- `callouts.py`: the rule is `fire_times` (`:14`), using estimates only: the first output sample where
  `reach = s + k·sigma >= exit_s - d` for `d` in 500, 200, 0 m (`:19`, `:23`). `ideal_times` (`:29`) is the truth-side
  reference; `missed_callouts` (`:56`) lists callouts the true vehicle reached but the estimator never fired.

- Monte Carlo (T9.1): `montecarlo.py` runs every scenario x seed x estimator in worker processes (`run_task`: one task = one scenario, variant and seed with all missing estimators) and appends one CSV row per vehicle and estimator to `docs/results/runs.csv` as each task finishes (`_append`; `_read_done` lets an interrupted run resume). Seed 0 is the scenario's own seed and the pf's default seed, so it reproduces single runs; seeds 1..N-1 come from `derive_seed` (`SeedSequence`) and also set the pf seed. The EKF counters (`gate_resets`, `beacon_updates`, `zupt_applied`, `zupt_gated`) are read from the estimator instances through a wrapper of `runner.get_estimator` inside the worker, so no estimator or runner code changed. The git column is the short hash plus `-dirty` outside `docs/results`. Side studies (`--study a30` / `beacon_sigma`) use `variants`: A30's `tilt_gyro_c1_deg_per_s` (1e-9, 0.02, 0.03 on `phone_handled_mid_tunnel` and `phone_in_hand_2min`) is overridden on `Aligner.default_params` inside the worker, and `watch_accel_use` wraps the EKF instance's `update` to record `accel_use_pct`, the share of IMU samples from the put-back to the tunnel exit on which the accelerometer was integrated (the trust rule of `ekf.py`, replicated from the aligned sample and the covariance; no estimator code changes); `beacon_sigma` is an estimator parameter. `summary.py` makes `summary.md` (accuracy and callout-timing tables), the box plots and the log-scale overview (|exit error| clipped at 0.1 m) from the CSV only. Commands: `make montecarlo ARGS="--seeds 50"`, `make montecarlo ARGS="--study a30"`, `make summary`. Results are committed by hand.

## 8. `sim/runner.py`: the glue

- `run_scenario` (`:127`): builds the road, the motions, the sensors, the estimator outputs, then the metrics and callouts,
  and returns a `Trace`. Truth is only used at `:157-173`.
- `_merged` (`:71`): all measurements as one list sorted by time, then by sensor order.
- `_run_estimators` (`:88`): for each output time, feed every measurement with `m.t <= t` to `update` (`:108-110`), then call
  `estimate(t)`. It also times each `update` call (`compute_us_per_measurement`).
- Estimator output rate is `rates_hz.output`; the estimators run at full sensor rates, the API only decimates the trace.

## 9. `sim/api` and `sim/cli.py`

`main.py` (FastAPI): `GET /api/scenarios` (`:35`), `GET /api/scenarios/{id}` (`:44`), (no save endpoint since T7.9: edits stay in memory), `GET /api/estimators` (`:72`), `GET /api/presets` (`:77`), `POST /api/montecarlo` (T9.4, end of file: `async`, runs `sim/api/mc.py::run` in a thread so the event loop and `/api/simulate` stay free),
`POST /api/simulate` (`:82`): validates estimator ids and parameters (`:90`), runs `run_scenario` (`:94`), decimates
(`decimate_hz` default 10), returns JSON without nulls. `cli.py` runs a scenario to a trace file.

`real.py` (T10.5a, an `APIRouter` included by `main.py`): `GET /api/real` lists the recordings in `data/real/` (id, span, default outage), `GET /api/real/{id}` returns the converted trace, `POST /api/real/{id}/run` takes the outage in recording time (start at least 60 s after the span start, end inside the span), fills the parameters the body leaves out from `REAL_DEFAULTS` (`replay.py`: `flat_grade` 0.03, `straight_curvature` 2e-3, relaxed for a hilly city drive, not validated on other drives; `bias_rw` stays 5e-4 because 0.01 fits only the default window) for the estimators that have them; `GET /api/real` lists them as `default_params`, and returns the same trace shape as `/api/simulate` with the outage as tunnel `T1`. Trace time counts from the span start (110 s).

`sim/realdata/sensor_logger.py` (T10.5a): `load_arrays` reads the Sensor Logger CSVs with the standard library and converts iOS signs and units (accelerometer `-G * raw`, lat/lon to ENU, bearing to ENU course), `build_map` fits a smoothing spline through the GNSS track (needs scipy; 1 m resolution, grade from the altitude) and returns `RoadMap.from_columns`, `convert` makes the trace (`source: "real"`, imu, gnss, truth `t, s, v` = GNSS projected on the map), `load_recording` caches it as JSON in `data/real/cache/` (git-ignored). `sim/realdata/replay.py::replay` removes the GNSS inside the window, declares it tunnel `T1`, runs the estimators with `runner._run_estimators` and computes the metrics against the partial truth.

Scripts in `tools/` (run from the repository root, not part of the simulator): `replay_real.py` replays a Sensor Logger folder with an outage window from the command line; `plot_real_replay.py` draws the write-up's Figure 4 (`docs/results/real_replay.png`); `diagnose_real.py` reproduces the real-drive numbers of write-up section 6.3 and Table 3 (stops, four outage windows, speed and forward-acceleration checks, the grade-at-true-position counterfactual; it reads the removed GNSS, so it is a diagnosis only).

## 10. `web/src`: the UI (React + Vite, plain JavaScript)

Pattern to keep: data-heavy layers are memoized and drawn once per trace; only small overlays depend on playback time `t`.

- `App.jsx`: the hub. `latest` ref (`:44`) holds the freshest state for handlers that fire after a render; `runWith` (`:47`)
  sends the scenario, the selected estimators with their params, and `callout_k`; responses of older runs are ignored (`runSeq`,
  `:46`, `run_done` check in `state.js:60`); `applyEdit` (`:59`) applies an edit action and runs when auto-run is on.
- Real recording (T10.5b): `state.source` is `sim` or `real`. In real mode the toolbar shows a recording picker and the two outage inputs (recording s), `App.jsx::runRecording` calls `runReal` (`api.js`) with every value in `realParams` (a second parameter store in `state.js`, started from the recording's `default_params` by `lib/realDefaults.js`; the Methods picker shows them in real mode and Reset restores them, T10.6c), auto-run is off, and the drive plan, scenario JSON editor, Settings columns and the Monte Carlo panel are not rendered (Settings shows only the Methods picker). In real mode the metrics table has no recovery column and `replay` leaves `recovery_time_s` empty: GNSS returns clean after the artificial outage, so recovery is always about 0 s and does not separate the methods (T10.6b). The "i" button shows the real-recording note (`Toolbar.jsx::REAL_NOTE`). The map, elevation, timeline and error chart place the truth marker from truth `s` through the map, so the real trace's partial truth works unchanged.
- `state.js: reducer` (`:18`): scenario (single source of truth), trace, selected estimators and params, `outdated` flag
  (`edit_scenario`, `:48`: an edit keeps the old trace on screen marked outdated).
- `api.js`: one function per endpoint; `simulate` (`:37`), `monteCarlo` (end of file).
- `components/MonteCarlo.jsx` (T9.4): panel under the metrics table. Seeds input, estimator checkboxes (default `DEFAULT_ON`: baseline, ekf_zupt, pf), Run, a log-y strip chart (`Strip`, one dot per seed, dash = median, values clipped at 0.1 m) and a median / p90 / consistency table (`Stats`). It sends the scenario and parameters currently in the panel; a tunnel select appears when the scenario has several tunnels.
- CSV columns (T9.5): next to `exit_error_m_t0..2` each row has `recovery_time_s_t0..2` (empty = never recovered) and `max_display_jump_m`, both from `compute_metrics`; `summary.py` shows median / p90 recovery, a not-recovered count and the median / max display jump.
- T11.1: `_imu` skips the stationary updates while the aligner is `in_hand` (the detector means nothing with a hand-held phone). The registry entry has `mc_default` (class attribute, default True; `ekf` sets False), which `MonteCarlo.jsx` uses for its preselection. `mc.start()` spawns the API pool when the server starts. `summary.py` treats a column missing in an old CSV as empty.
- Live Monte Carlo (T9.4): `sim/api/mc.py` builds one task per seed with `montecarlo.inline_tasks` (the scenario object and UI parameters travel in the task `settings`, which `run_task` accepts as `scenario` / `params`) and runs them in a persistent spawn `ProcessPoolExecutor`. The first wave's task times (`timed_task`) give a projected runtime; above 60 s the rest is cancelled and the request gets a 422. One run at a time (409 otherwise). `summarize` returns signed exit errors per tunnel, consistency per run, median / p90 of |exit error|. No CSV. Pool workers ignore SIGINT (`montecarlo.ignore_sigint`), and `mc.shutdown` stops the API pool in the app's lifespan.
- Sweeps (T9.2): `sweep.py` reuses the Monte Carlo machinery (`montecarlo.execute`, `plan_tasks`, the resumable CSV) with one varied simulator setting per variant label: `accel_bias` multiplies the simulated phone's accelerometer bias (constant part and drift, A14) through `scaled_preset`, patched over `runner.load_preset` in the worker, so the estimators keep assuming the original phone; `tunnel_length` rebuilds a straight scenario with `with_tunnel_length` (tunnel 0.5-5 km, 1.5 km of road after it, exit 300 m after it). CSVs: `docs/results/sweeps/<name>.csv`; `make sweep ARGS="--sweep accel_bias --seeds 30"`; `make figures` regenerates every table and figure (main, side studies, sweeps) from the CSVs; per sweep a summary table, median |exit error| against the value (log y, one panel per scenario) and mean consistency.
- Estimator markers (T7.2-CR4): each estimator has a colour (`colors.js: estimatorColor`) and a hollow shape (`estimatorShape`: circle, triangle, square, diamond, assigned by registry order like the colour, so no estimator name is hardcoded). `EstimatorMarker.jsx` draws it; the map, the elevation profile and the map legend use it. Reason: `ekf` and `ekf_zupt` give identical estimates without stops (e.g. `curved_5km_exit_inside`), so the later-drawn marker hid the other.
- Map view rotation (T7.2-CR3): `lib/mapProjection.js` (`roadRotation`: angle that turns the road's first-to-last-point line left to right; `project`: world to screen pixels; `screenToWorldOffset`: the inverse for pan and wheel zoom). `MapView` holds `northUp` (default off, `rot = 0` when on) and passes `rot` to `RoadPaths` (an SVG `rotate` in the view transform), `ExitLayer` and `MapDynamic` (they project positions, so markers, labels and bars stay upright and keep their pixel sizes). `NorthArrow.jsx` points to world north on screen. Data and traces are not changed.
- Map: `MapView.jsx`, `MapStatic.jsx` (memoized `RoadPaths`, `ExitLayer`), `MapDynamic.jsx` (`:10`, car and estimate markers
  that depend on `t`: the marker sits at `display_s`, the ±2σ bar around `s`, and a thin second ring at `s` only when the two differ by more than 5 m, `estimateAt` in `lib/trace.js`), `ScaleBar.jsx`. `ElevationProfile.jsx`: `ProfileStatic` (`:37`, memoized) and markers (same display_s / raw s rule as the map).
- Playback: `lib/usePlayback.js` (`:7`): `t`, play/pause, speed, seek, keyboard shortcuts; the `requestAnimationFrame` loop is
  `tick` (`:41`). `Timeline.jsx`: slider, tunnel bands, event jumps. `lib/interp.js: interpAt` (`:14`) reads a column at
  time `t`.
- Charts: `ChartStack.jsx` (`:15` click-to-seek) measures the width and draws the one shared cursor; all charts use the
  geometry in `lib/plotGeometry.js` (`timeToX`, `xToTime`, `:12-15`) so one x mapping fits all. `ErrorChart.jsx`:
  `buildRows` (`:14`) → error line and ±2σ band per estimator, `staggerLabels` (`:46`) for the callout labels. The "Bands" select (T10.6d): Overlay (all lines and bands in one plot), Separate (one 140 px row per method, `Plot` called once per method, every row on the y range from `sharedDomain`: the min and max of error ± 2σ over all methods, rounded outwards to a 1-2-5 step; the fixed ±50 / ±200 choices apply to every row) and Off (lines only). One method selected: Separate falls back to Overlay.
  `SensorCharts.jsx` (`:52`; each chart's title and series legend sit in a strip above the plot area, `TITLE_H`; the error chart does the same; `lib/plotGeometry.js` `Y_PAD` and `X_TICK_MARGIN` keep tick labels off the axes) with `lib/sensorSeries.js` (`buildCharts`, `:33`; `breakGaps`, `:15` inserts nulls so GNSS lines
  break in tunnels). Recharts never receives `t`.
- `MetricsTable.jsx`: columns are generated from the metrics present (`buildColumns`, `:13`); best value per column
  (`bestRows`, `:39`).
- Settings panel (T7.9; no right column any more): the header has a "Settings" button and, while the panel is closed (default), a one-line summary (`lib/summary.js: settingsSummary`). `Controls.jsx` is the open panel (`Slider`; full width, three columns Road and tunnel / Phone and sensors / Methods and, in its own full-width row below them, the Driving plan; the phone select shows each preset's `name`, `presets/*.json`, with Auto-run, Edit JSON and Reset to default on top; the Methods column is the `EstimatorPicker` passed in as `methods`; the controls read their value from the scenario), `lib/scenarioEdits.js` (pure
  functions, each returns a new scenario: `setTunnelLength`, `extendRoad`, `addPlanPoint`, `editPlanPoint`, `deletePlanPoint`),
  `DrivingPlan.jsx` (one labelled line per plan point, e.g. "at 2.0 km → 90 km/h, rate 1.5 m/s²"; each field group is `nowrap`, a long row wraps only between groups; `Num` commits on Enter or blur),
  `EstimatorPicker.jsx` (`ParamInput`, `:14`; `BoolInput` checkbox for `bool` constraints); the parameters of one method sit in one CSS grid (`.params`: name | input | unit, the unit cell is always rendered), so all inputs line up (T10.6a), `JsonEditor.jsx` (`describe`, `:4`: JSON error with line and column),
  `Panel.jsx` (results and the "outdated" banner, a full-width strip above the map), `Toolbar.jsx` (the dropdown shows each scenario's `title`; the "i" button opens `InfoModal.jsx` with the full description, closed by its button, Escape or a click outside).
- `ErrorBoundary.jsx` wraps each view so one crash does not blank the page (`getDerivedStateFromProps` resets it on a new
  trace, `:11`).
- Colors: `colors.js: estimatorColor` (`:6`), one color per estimator in registry order. No estimator name is hard-coded in
  `web/`.

## 11. Where truth isolation and causality are enforced

Truth isolation (estimators never see truth):

1. The only input an estimator gets is a `Measurement(t, kind, data)` (`sim/contracts/estimation.py:15`), built from the
   sensor columns; truth is not a field of it.
2. `_run_estimators` is called with `sensors` and `road_map` only (`sim/runner.py:153-156`); `truth` is built afterwards
   (`:157`) and goes only to `compute_callouts` / `compute_metrics`.
3. Estimators import only `sim.contracts.estimation`, `sim.world.road`, `sim.geometry.so3` and each other (the import lines of
   `sim/estimators/*.py`: `alignment.py:18-20`, `baseline.py:7-9`, `ekf.py:8-12`; `stationary.py` imports only the standard library). They do not import
   `sim.sensors`, `sim.eval`, `sim.runner` or `sim.world.vehicle`. This is enforced: the end of
   `tests/test_runner.py::test_estimator_sees_only_measurements_in_time_order` parses every `sim/estimators/*.py` with `ast`
   and fails on such an import (also `from sim import sensors` and `from sim.world import vehicle`).
4. The same test records everything a spy estimator is given: only `Measurement`s, in time order.

Causality (state changes only through `update(m)`, in time order):

1. `_merged` sorts by time (`sim/runner.py:71`); `_run_estimators` feeds `stream[i].t <= t` before `estimate(t)` (`:108-110`).
2. `estimate()` only reads state (`ekf.py:264`, `baseline.py:62`); `Aligner` state changes only in `process_gnss` /
   `process_imu`. The Aligner's delays (0.3 s staging, 0.2 s detection) are causal: it never looks ahead.
3. All randomness comes from seeded generators passed in; no `np.random` global (`sim/runner.py:134-138`).

## 12. How do I change ...

### ... change how the car drives
Edit `vehicles[0].plan` in the scenario (`docs/CONTRACTS.md` 3.2) or use the "Driving plan" table in the UI. A new plan point type: model in `scenario.py`, a `_Run` method in `vehicle.py`, a branch in `simulate_vehicle` and `_check_plan`. The "Speed fluctuation" slider stops at 6 km/h: measured on 8 seeds at 70 km/h, 6 gives a peak jerk of 1.97 m/s³ (A11 limit 2.0), 10 gives 3.3 and 15 gives 4.9 (peak acceleration 5.2 m/s²).

### ... add a scenario
1. Copy a file in `scenarios/` to `scenarios/<id>.json`; set `"id"` to the file name without `.json` (checked by
   `tests/test_scenarios.py`), a new `"seed"`, a non-empty `"title"` (the name in the dropdown; the listing falls back to the id) and a non-empty `"description"`.
2. Add a row to `scenarios/README.md`.
3. `tests/test_api.py` asserts the scenario count and `tests/test_scenarios.py` a minimum: update both numbers.
4. `python -m pytest -q`. No frontend change: the picker reads `/api/scenarios`. Scenarios cannot be saved from the UI any more (T7.9); edit the file, or edit in the UI and copy the JSON from "Edit JSON".

### ... change a sensor noise value
1. Datasheet-style values (noise density, bias, scale error, GNSS std, baro noise): `presets/flagship_2024.json` (and
   `presets/budget.json`, A16: the budget values are fixed multiples). Change `value` **and** `source` (the schema,
   `sim/contracts/preset.py:12`, rejects an empty source).
2. Vibration and handling constants: top of `sim/sensors/imu.py` (`:13-20`, A17). BLE: `sim/sensors/ble.py:10-11`.
3. Update the matching A-number in `docs/ASSUMPTIONS.md`; run `python -m pytest -q` (`tests/test_imu.py`, `test_gnss.py`, ...).

### ... change a tunnel effect
1. Strengths are scenario fields: `tunnel_env.pressure_step_pa`, `fan_pressure_noise_pa` (no UI control since T7.7-CR1: no estimator reads the barometer; edit it in Edit JSON), `mag_disturbance_ut`, and
   `gnss_env.*` (portal degradation, reacquire delay, bad fixes). Edit in the scenario JSON, or in the UI.
2. Shapes and time constants: pressure step `baro.py:21` (`TAU_STEP_S`, `:10`, A21), fan `baro.py:38` (`TAU_FAN_S`, `:11`,
   A22), magnetic field `mag.py:16` (`CORR_LENGTH_M`, `:13`, A23), GNSS portal growth `gnss.py:15` (`PORTAL_GROWTH`, `:10`, A19).
3. To expose a new field in the scenario: add it to the model in `sim/contracts/scenario.py` (and `docs/CONTRACTS.md` 3.2 first,
   with approval), then read it in the sensor.

### ... add or change an estimator parameter
1. In the estimator class: add it to `default_params`, `constraints` and `param_info` (`ekf.py:30-60`; the registry test fails without a label and a description); read it in `reset`
   (`setattr` loop, `ekf.py:47`), use it where needed. For the ZUPT parameters, the same in `EkfZuptEstimator` (`ekf.py:280`).
2. Nothing else for the UI: `/api/estimators` returns it, `EstimatorPicker` shows an input with the label, unit and an "i" with the description (`ParamName`) and the right limits, `Run` sends it,
   `/api/simulate` validates it (`registry.validate_params`).
3. Document the value and why in `docs/ASSUMPTIONS.md` (A31 for the EKF); `python -m pytest -q`.
4. A new estimator: a class with `id`, `label`, `default_params`, `constraints`, `param_info`, `reset`, `update`, `estimate`, decorated with
   `@register`, imported in `sim/estimators/__init__.py`. It appears in the UI by itself.

### ... change the callout rule or k
1. The rule: `fire_times` in `sim/eval/callouts.py:14-26` (`reach >= exit_s - d`); the distances are `DISTANCES_M` (`:11`).
2. `k` is not part of the scenario: UI slider (`Controls.jsx`) → `state.calloutK` → `simulate(..., calloutK)`
   (`web/src/api.js:37`) → `SimulateRequest.callout_k` (`sim/api/main.py:28`) → `run_scenario` → `compute_callouts`
   (`sim/runner.py:162`).
3. If you add a distance: also `DISTANCES` in `web/src/components/MetricsTable.jsx:4`. Tests: `tests/test_callouts.py`.

### ... add a metric and show it in the table
1. Compute it in `compute_metrics` (`sim/eval/metrics.py:34`): add a key to `out`; leave it out (or `None`) when undefined.
2. Document it in `docs/CONTRACTS.md` 3.5.
3. Table: add a column in `buildColumns` (`web/src/components/MetricsTable.jsx:13`): `{ key, label, get: (m) => m.<name>,
   fmt, score }`; `score` decides which value is highlighted as best (smallest `score`).
4. Test in `tests/test_metrics.py` with a small synthetic input.

### ... add a UI control that edits the scenario
1. A pure function in `web/src/lib/scenarioEdits.js`: takes a scenario, returns a new one (it must not mutate the old one).
2. A control in `web/src/components/Controls.jsx`: a `Slider` or input whose value is read from the scenario; wire `onChange`
   with `live(fn)` (JSON only, for drags) and `onCommit` / `now(fn)` (also runs, when auto-run is on).
3. Check that the edited scenario still validates (run it; the API shows the error), and that the JSON editor shows the change.
   There is no state change to make: the scenario in state is the single source of truth.

## 13. Test map

| Test file | Covers |
| --- | --- |
| `test_scenario.py` | scenario schema: example validates; tunnel/exit off the road and unknown plan types rejected |
| `test_scenarios.py` | every file in `scenarios/` validates, id equals the file name, has a title and a description, and runs |
| `test_road.py` | length, grade, arc heading and map projection, `in_tunnel` |
| `test_vehicle.py` | stop is exact and speed non-negative, same seed same result, lateral acceleration in a curve, follower keeps its gap, plan points met at their position (slowdown within 5 m, speed-up starts at its point, stop within 1 m with its dwell) |
| `test_imu.py` | presets validate and need a source; at rest the acceleration norm ≈ g; gyro z = v·curvature; inverse transform returns the true acceleration |
| `test_handling_gyro.py` | integrating the gyro over a 4 s and a 120 s handling event recovers the mount change (< 0.1°) |
| `test_gnss.py` | no fixes inside tunnels, bad fixes after exit, open-sky error matches the preset |
| `test_baro.py` | 10 m climb ≈ 1.2 hPa; with tunnel effects off only noise remains |
| `test_mag.py` | noise-free norm and heading on a grade; no disturbance outside tunnels |
| `test_ble.py` | RSSI peaks at the passing time; disabled beacons give no rows |
| `test_trace.py` | trace round trip and decimation |
| `test_estimators.py` | registry: register/list, removal, estimator types are slotted |
| `test_baseline.py` | baseline: small exit error at constant speed, large on stop-and-go |
| `test_alignment.py` | Aligner on noise-free data: mount yaw and gyro bias found, handling detected and re-aligned, no false detection |
| `test_pf.py` | particle filter: `curved_5km_exit_inside` in-tunnel RMSE below `ekf_zupt`; `undersea_3km_dip` exit error bounded |
| `test_ekf.py` | EKF in-tunnel consistency on `curved_2km`; EKF+ZUPT in-tunnel RMSE below half of the EKF's on `hard_brake_inside`; the beacon peak time of a symmetric pass is the true pass time (the moving-average delay is removed); a `v = 0` update with `keep_s=False` leaves s unchanged; beacons bound the `beacons_5km` error (RMSE < 20 m) and change nothing without beacons (the 15 s standstill); the stationary detector never fires on the raw IMU of the constant-speed `curved_2km` and `beacons_5km`; EKF+ZUPT `display_s` is non-decreasing, its max display jump is below the baseline's and recovery exists in `short_straight_500m`, `hard_brake_inside`, `stop_and_go_3km` (T8.6) |
| `test_realdata.py` | real drive (skipped without the recording): iOS sign checks (accelerometer z about +g, gyro z correlates with the GNSS course rate), `/api/real` list and a baseline run with the default window, 422 for a window with under 60 s of GNSS before it |
| `test_metrics.py` | RMSE, exit error, consistency, recovery time |
| `test_sweep.py` | the sweep with N = 2, two values and one short scenario into a temporary directory: CSV rows per value, figures made from the CSV |
| `test_montecarlo.py` | N = 2 on `short_straight_500m` into a temporary directory: CSV columns, resume adds nothing, summary table |
| `test_callouts.py` | perfect estimate fires at the ideal time; larger k fires earlier; missed callouts |
| `test_runner.py` | same seed is byte-identical (without the wall-clock `compute_us_per_measurement`); an estimator sees only time-ordered measurements, and no estimator module imports sensor, eval, runner or vehicle code (`ast` check); changing the GNSS preset keeps the IMU identical |
| `test_api.py` | endpoints, Monte Carlo with 2 seeds, simulate returns a decimated trace, invalid inputs and bad parameters give 422, an estimator crash gives 422 |
| `test_health.py` | `/api/health` |

The frontend has no automated tests; it is checked by `npm run build`, `npx oxlint` and by hand in the browser.
