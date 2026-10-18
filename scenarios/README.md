# Scenarios

Each file is a scenario as defined in `docs/CONTRACTS.md` section 3.2; its `description` says what it tests. Scenario values are test conditions chosen for this case study, not device parameters, so they carry no `source` field. All scenarios have at least 60 s of good GNSS before the first tunnel (A4) and at least 1 km of open road after the last one, so recovery can be measured.

| Scenario | Tunnel | What it tests |
| --- | --- | --- |
| `curved_3km_exit_inside` | 3 km, two curves, mild grades, one stop | The contract example from the plan |
| `short_straight_500m` | 0.5 km straight, flat | Easiest case; callouts around GNSS recovery |
| `curved_2km` | 2 km, two curves, flat | Curvature as a map feature |
| `curved_5km_exit_inside` | 5 km, two curves, flat | Longest outage; callouts after 4+ min without GNSS |
| `undersea_3km_dip` | 3 km straight, -4% / flat / +4% | Barometer as a map feature |
| `stop_and_go_3km` | 3 km straight, flat, 2 km of traffic | Baseline failure; stop detection (ZUPT) |
| `hard_brake_inside` | 2 km straight, flat, 6 m/s² stop | Sudden speed change |
| `phone_handled_mid_tunnel` | 3 km straight, flat | Handling detection and re-alignment |
| `convoy_3_cars` | 2.5 km straight, flat | Several vehicles, slow leader, queue at a stop |
| `budget_phone_5km` | same as `curved_5km_exit_inside` | Effect of a budget phone (same seed, same true motion) |
| `twin_tunnels_short_gap` | 2 × 1.5 km, 200 m gap | Short GNSS window with bad fixes |
| `beacons_5km` | 5 km straight, flat, beacons every 400 m | Beacon fixes; with beacons off, the no-map-feature honest failure |
