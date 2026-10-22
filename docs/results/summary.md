# Monte Carlo summary

3000 rows, commit 59d919a. `Runs` counts rows (vehicle x seed). Exit error is signed in the CSV; the table uses its absolute value (per tunnel where a scenario has several). Consistency is the share of tunnel samples with |error| < 2 sigma. Timing error is t - t_ideal (positive = late). Time per measurement was measured with several processes running in parallel, so only the ratios are meaningful.

## Accuracy

| Scenario | Estimator | Tunnel | Runs | Median abs. exit error (m) | p90 abs. exit error (m) | Median RMSE (m) | Mean consistency (%) | Missed callouts | Median time (µs/meas.) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| beacons_5km | baseline |  | 50 | 111.3 | 234.7 | 66.1 | 98.3 | 0 | 0.3 |
| beacons_5km | ekf |  | 50 | 10.2 | 13.9 | 10.9 | 64.2 | 0 | 23.8 |
| beacons_5km | ekf_zupt |  | 50 | 10.2 | 13.9 | 10.9 | 64.2 | 0 | 25.1 |
| beacons_5km | pf |  | 50 | 9.2 | 14.0 | 10.9 | 50.2 | 0 | 33.4 |
| budget_phone_5km | baseline |  | 50 | 110.6 | 251.8 | 68.1 | 98.1 | 0 | 0.3 |
| budget_phone_5km | ekf |  | 50 | 303.6 | 611.1 | 133.3 | 93.8 | 0 | 28.1 |
| budget_phone_5km | ekf_zupt |  | 50 | 303.6 | 611.1 | 133.3 | 93.8 | 0 | 29.5 |
| budget_phone_5km | pf |  | 50 | 38.8 | 93.4 | 19.6 | 95.6 | 0 | 41.6 |
| curved_2km | baseline |  | 50 | 28.8 | 81.3 | 20.0 | 98.3 | 0 | 0.4 |
| curved_2km | ekf |  | 50 | 37.5 | 76.6 | 21.2 | 98.1 | 0 | 30.3 |
| curved_2km | ekf_zupt |  | 50 | 37.5 | 76.6 | 21.2 | 98.1 | 0 | 32.4 |
| curved_2km | pf |  | 50 | 9.7 | 17.1 | 8.7 | 96.5 | 0 | 42.1 |
| curved_3km_exit_inside | baseline |  | 50 | 1218.5 | 1366.5 | 818.7 | 24.1 | 0 | 0.4 |
| curved_3km_exit_inside | ekf |  | 50 | 62.6 | 264.0 | 24.3 | 98.9 | 0 | 30.7 |
| curved_3km_exit_inside | ekf_zupt |  | 50 | 41.7 | 95.4 | 20.8 | 71.5 | 0 | 32.6 |
| curved_3km_exit_inside | pf |  | 50 | 5.9 | 14.0 | 28.1 | 98.6 | 0 | 44.3 |
| curved_5km_exit_inside | baseline |  | 50 | 100.2 | 262.8 | 61.2 | 96.6 | 0 | 0.4 |
| curved_5km_exit_inside | ekf |  | 50 | 149.9 | 332.9 | 69.8 | 97.3 | 0 | 28.7 |
| curved_5km_exit_inside | ekf_zupt |  | 50 | 149.9 | 332.9 | 69.8 | 97.3 | 0 | 30.4 |
| curved_5km_exit_inside | pf |  | 50 | 21.5 | 41.7 | 12.5 | 97.7 | 0 | 42.3 |
| hard_brake_inside | baseline |  | 50 | 559.8 | 665.5 | 396.3 | 37.0 | 0 | 0.4 |
| hard_brake_inside | ekf |  | 50 | 24.2 | 69.9 | 12.7 | 87.3 | 0 | 30.0 |
| hard_brake_inside | ekf_zupt |  | 50 | 9.8 | 24.4 | 5.3 | 75.7 | 0 | 32.2 |
| hard_brake_inside | pf |  | 50 | 9.6 | 26.2 | 6.1 | 93.7 | 0 | 42.7 |
| phone_handled_mid_tunnel | baseline |  | 50 | 47.8 | 142.6 | 26.7 | 98.8 | 0 | 0.4 |
| phone_handled_mid_tunnel | ekf |  | 50 | 46.2 | 117.7 | 22.7 | 95.0 | 0 | 28.5 |
| phone_handled_mid_tunnel | ekf_zupt |  | 50 | 46.2 | 117.7 | 22.7 | 95.0 | 0 | 30.2 |
| phone_handled_mid_tunnel | pf |  | 50 | 45.1 | 111.2 | 22.6 | 97.1 | 0 | 41.9 |
| phone_in_hand_2min | baseline |  | 50 | 73.3 | 207.1 | 44.6 | 96.6 | 0 | 0.4 |
| phone_in_hand_2min | ekf |  | 50 | 101.6 | 220.9 | 56.2 | 97.6 | 0 | 35.1 |
| phone_in_hand_2min | ekf_zupt |  | 50 | 101.6 | 220.9 | 56.2 | 97.6 | 0 | 37.0 |
| phone_in_hand_2min | pf |  | 50 | 11.7 | 27.5 | 37.5 | 97.9 | 0 | 53.8 |
| phone_in_hand_whole_trip | baseline |  | 50 | 72.9 | 175.1 | 43.8 | 99.9 | 0 | 0.4 |
| phone_in_hand_whole_trip | ekf |  | 50 | 89.1 | 203.2 | 51.9 | 99.2 | 0 | 44.1 |
| phone_in_hand_whole_trip | ekf_zupt |  | 50 | 89.1 | 203.2 | 51.9 | 99.2 | 0 | 46.0 |
| phone_in_hand_whole_trip | pf |  | 50 | 97.6 | 232.1 | 60.2 | 99.1 | 0 | 62.1 |
| short_straight_500m | baseline |  | 50 | 13.2 | 28.3 | 10.2 | 99.6 | – | 0.6 |
| short_straight_500m | ekf |  | 50 | 2.5 | 6.3 | 1.7 | 82.8 | – | 33.9 |
| short_straight_500m | ekf_zupt |  | 50 | 2.5 | 6.3 | 1.7 | 82.8 | – | 36.1 |
| short_straight_500m | pf |  | 50 | 2.5 | 6.3 | 1.7 | 84.1 | – | 44.0 |
| speed_changes_3km | baseline |  | 50 | 1012.5 | 1289.2 | 579.8 | 24.2 | 0 | 0.4 |
| speed_changes_3km | ekf |  | 50 | 81.0 | 238.1 | 34.7 | 91.3 | 0 | 30.9 |
| speed_changes_3km | ekf_zupt |  | 50 | 81.0 | 238.1 | 34.7 | 91.3 | 0 | 32.9 |
| speed_changes_3km | pf |  | 50 | 85.4 | 242.7 | 36.1 | 94.7 | 0 | 45.2 |
| stop_and_go_3km | baseline |  | 50 | 1500.0 | 1500.0 | 1834.8 | 8.5 | 0 | 0.3 |
| stop_and_go_3km | ekf |  | 50 | 100.0 | 809.7 | 57.4 | 96.2 | 0 | 29.8 |
| stop_and_go_3km | ekf_zupt |  | 50 | 78.5 | 104.3 | 42.5 | 20.0 | 0 | 32.3 |
| stop_and_go_3km | pf |  | 50 | 53.2 | 98.0 | 26.0 | 98.9 | 0 | 47.4 |
| traffic_before_tunnel | baseline |  | 50 | 491.1 | 793.8 | 272.9 | 36.7 | 0 | 0.6 |
| traffic_before_tunnel | ekf |  | 50 | 49.6 | 120.2 | 22.9 | 93.9 | 0 | 42.2 |
| traffic_before_tunnel | ekf_zupt |  | 50 | 43.3 | 114.9 | 21.4 | 95.0 | 0 | 45.0 |
| traffic_before_tunnel | pf |  | 50 | 47.4 | 115.5 | 20.7 | 96.1 | 0 | 55.6 |
| twin_tunnels_short_gap | baseline | T0 | 50 | 32.2 | 66.0 | 22.1 | 98.3 | 0 | 0.4 |
| twin_tunnels_short_gap | baseline | T1 | 50 | 23.2 | 70.3 |  |  | – |  |
| twin_tunnels_short_gap | ekf | T0 | 50 | 11.7 | 34.5 | 6.6 | 91.7 | 0 | 32.0 |
| twin_tunnels_short_gap | ekf | T1 | 50 | 12.1 | 31.7 |  |  | – |  |
| twin_tunnels_short_gap | ekf_zupt | T0 | 50 | 11.7 | 34.5 | 6.6 | 91.7 | 0 | 34.0 |
| twin_tunnels_short_gap | ekf_zupt | T1 | 50 | 12.1 | 31.7 |  |  | – |  |
| twin_tunnels_short_gap | pf | T0 | 50 | 11.5 | 34.8 | 6.7 | 93.5 | 0 | 45.5 |
| twin_tunnels_short_gap | pf | T1 | 50 | 10.7 | 32.5 |  |  | – |  |
| undersea_3km_dip | baseline |  | 50 | 63.4 | 162.3 | 39.7 | 97.4 | 0 | 0.5 |
| undersea_3km_dip | ekf |  | 50 | 20.1 | 42.8 | 14.0 | 94.3 | 0 | 32.0 |
| undersea_3km_dip | ekf_zupt |  | 50 | 20.1 | 42.8 | 14.0 | 94.3 | 0 | 34.1 |
| undersea_3km_dip | pf |  | 50 | 20.0 | 43.5 | 13.6 | 95.7 | 0 | 46.0 |

## Callout timing

| Scenario | Estimator | 500 m: median / median abs. / p90 abs. (s) | 200 m: median / median abs. / p90 abs. (s) | 0 m: median / median abs. / p90 abs. (s) |
| --- | --- | --- | --- | --- |
| beacons_5km | baseline | -5.2 / 5.4 / 13.0 | -5.7 / 5.7 / 14.0 | -5.9 / 6.0 / 14.6 |
| beacons_5km | ekf | +0.1 / 0.2 / 0.3 | +0.2 / 0.2 / 0.4 | +0.0 / 0.2 / 0.4 |
| beacons_5km | ekf_zupt | +0.1 / 0.2 / 0.3 | +0.2 / 0.2 / 0.4 | +0.0 / 0.2 / 0.4 |
| beacons_5km | pf | +0.2 / 0.2 / 0.4 | +0.3 / 0.3 / 0.4 | +0.1 / 0.2 / 0.3 |
| budget_phone_5km | baseline | -8.4 / 8.4 / 14.7 | -8.9 / 8.9 / 16.0 | -9.4 / 9.4 / 16.6 |
| budget_phone_5km | ekf | -15.6 / 15.6 / 27.6 | -15.0 / 16.1 / 29.1 | -15.3 / 19.0 / 29.4 |
| budget_phone_5km | ekf_zupt | -15.6 / 15.6 / 27.6 | -15.0 / 16.1 / 29.1 | -15.3 / 19.0 / 29.4 |
| budget_phone_5km | pf | -0.6 / 0.6 / 1.0 | -1.5 / 1.5 / 2.5 | -2.4 / 2.4 / 3.8 |
| curved_2km | baseline | -1.5 / 1.6 / 2.8 | -1.8 / 1.9 / 3.6 | -2.1 / 2.2 / 4.3 |
| curved_2km | ekf | -3.1 / 3.1 / 4.4 | -4.5 / 4.5 / 6.5 | -5.5 / 5.5 / 8.4 |
| curved_2km | ekf_zupt | -3.1 / 3.1 / 4.4 | -4.5 / 4.5 / 6.5 | -5.5 / 5.5 / 8.4 |
| curved_2km | pf | -0.8 / 0.8 / 1.3 | -1.8 / 1.8 / 2.8 | +0.3 / 0.5 / 1.5 |
| curved_3km_exit_inside | baseline | -49.0 / 49.0 / 51.1 | -52.1 / 52.1 / 54.3 | -54.1 / 54.1 / 57.0 |
| curved_3km_exit_inside | ekf | -12.3 / 12.3 / 16.6 | -12.7 / 12.7 / 15.6 | -14.1 / 14.1 / 17.4 |
| curved_3km_exit_inside | ekf_zupt | +0.5 / 0.6 / 1.7 | +0.6 / 0.6 / 1.7 | +0.6 / 0.7 / 1.7 |
| curved_3km_exit_inside | pf | -5.7 / 5.7 / 8.1 | -6.9 / 6.9 / 9.8 | -7.7 / 7.7 / 10.9 |
| curved_5km_exit_inside | baseline | -8.2 / 8.2 / 14.7 | -8.7 / 8.7 / 15.8 | -9.2 / 9.2 / 16.5 |
| curved_5km_exit_inside | ekf | -13.0 / 13.0 / 20.2 | -13.6 / 13.6 / 20.8 | -13.2 / 13.2 / 21.6 |
| curved_5km_exit_inside | ekf_zupt | -13.0 / 13.0 / 20.2 | -13.6 / 13.6 / 20.8 | -13.2 / 13.2 / 21.6 |
| curved_5km_exit_inside | pf | -0.5 / 0.5 / 0.6 | -1.2 / 1.2 / 1.6 | -1.7 / 1.7 / 2.4 |
| hard_brake_inside | baseline | -27.3 / 27.3 / 29.2 | -27.4 / 27.4 / 29.8 | -27.5 / 27.5 / 30.5 |
| hard_brake_inside | ekf | -1.2 / 1.2 / 2.7 | -1.6 / 1.6 / 3.4 | -1.9 / 1.9 / 4.0 |
| hard_brake_inside | ekf_zupt | +0.0 / 0.1 / 0.6 | +0.0 / 0.2 / 0.7 | +0.0 / 0.3 / 0.7 |
| hard_brake_inside | pf | -1.2 / 1.2 / 1.9 | -1.5 / 1.5 / 2.2 | -1.8 / 1.8 / 2.4 |
| phone_handled_mid_tunnel | baseline | -2.4 / 2.8 / 7.2 | -2.8 / 3.1 / 8.1 | -3.0 / 3.5 / 9.0 |
| phone_handled_mid_tunnel | ekf | -2.1 / 2.2 / 3.8 | -3.3 / 3.3 / 5.3 | -4.2 / 4.2 / 6.2 |
| phone_handled_mid_tunnel | ekf_zupt | -2.1 / 2.2 / 3.8 | -3.3 / 3.3 / 5.3 | -4.2 / 4.2 / 6.2 |
| phone_handled_mid_tunnel | pf | -2.5 / 2.5 / 4.3 | -3.7 / 3.7 / 5.6 | -4.8 / 4.8 / 6.6 |
| phone_in_hand_2min | baseline | -5.3 / 5.9 / 11.1 | -5.7 / 6.3 / 11.9 | -5.9 / 6.4 / 12.6 |
| phone_in_hand_2min | ekf | -19.3 / 19.3 / 24.5 | -21.6 / 21.6 / 27.2 | -23.1 / 23.1 / 29.0 |
| phone_in_hand_2min | ekf_zupt | -19.3 / 19.3 / 24.5 | -21.6 / 21.6 / 27.2 | -23.1 / 23.1 / 29.0 |
| phone_in_hand_2min | pf | -0.6 / 0.6 / 0.8 | -1.7 / 1.7 / 2.1 | -2.4 / 2.4 / 3.0 |
| phone_in_hand_whole_trip | baseline | -6.1 / 6.1 / 11.2 | -6.5 / 6.5 / 12.0 | -6.8 / 6.8 / 12.6 |
| phone_in_hand_whole_trip | ekf | -22.5 / 22.5 / 25.7 | -25.1 / 25.1 / 28.4 | -26.6 / 26.6 / 30.0 |
| phone_in_hand_whole_trip | ekf_zupt | -22.5 / 22.5 / 25.7 | -25.1 / 25.1 / 28.4 | -26.6 / 26.6 / 30.0 |
| phone_in_hand_whole_trip | pf | -23.0 / 23.0 / 26.4 | -25.5 / 25.5 / 28.9 | -27.2 / 27.2 / 30.8 |
| speed_changes_3km | baseline | -48.8 / 48.8 / 56.1 | -51.5 / 51.5 / 60.3 | -53.4 / 53.4 / 62.3 |
| speed_changes_3km | ekf | -4.3 / 5.1 / 10.6 | -5.8 / 5.9 / 12.6 | -6.3 / 7.2 / 13.9 |
| speed_changes_3km | ekf_zupt | -4.3 / 5.1 / 10.6 | -5.8 / 5.9 / 12.6 | -6.3 / 7.2 / 13.9 |
| speed_changes_3km | pf | -4.8 / 5.1 / 11.0 | -6.2 / 6.4 / 12.7 | -7.0 / 7.2 / 14.1 |
| stop_and_go_3km | baseline | -227.1 / 227.1 / 257.7 | -275.2 / 275.2 / 297.3 | -282.5 / 282.5 / 304.1 |
| stop_and_go_3km | ekf | -65.3 / 65.3 / 97.8 | -86.2 / 86.2 / 128.7 | -77.4 / 77.4 / 122.1 |
| stop_and_go_3km | ekf_zupt | +6.5 / 6.5 / 22.4 | +5.5 / 5.5 / 10.2 | +3.8 / 3.8 / 5.2 |
| stop_and_go_3km | pf | -42.7 / 42.7 / 53.3 | -51.4 / 51.4 / 64.1 | -25.6 / 25.6 / 54.3 |
| traffic_before_tunnel | baseline | -23.2 / 23.2 / 31.8 | -28.6 / 28.6 / 38.5 | -28.6 / 28.6 / 39.5 |
| traffic_before_tunnel | ekf | -3.7 / 3.9 / 8.6 | -3.2 / 3.4 / 6.7 | -3.7 / 3.7 / 6.8 |
| traffic_before_tunnel | ekf_zupt | -3.4 / 4.1 / 7.7 | -2.5 / 2.8 / 5.6 | -2.9 / 3.2 / 5.9 |
| traffic_before_tunnel | pf | -4.9 / 5.0 / 8.5 | -3.3 / 3.3 / 5.9 | -3.7 / 3.7 / 6.5 |
| twin_tunnels_short_gap | baseline | -1.1 / 1.1 / 2.0 | -1.5 / 1.6 / 3.0 | -1.8 / 1.9 / 3.5 |
| twin_tunnels_short_gap | ekf | -0.1 / 0.2 / 0.7 | -0.2 / 0.3 / 0.9 | -0.4 / 0.5 / 1.2 |
| twin_tunnels_short_gap | ekf_zupt | -0.1 / 0.2 / 0.7 | -0.2 / 0.3 / 0.9 | -0.4 / 0.5 / 1.2 |
| twin_tunnels_short_gap | pf | -0.2 / 0.2 / 0.7 | -0.4 / 0.4 / 1.0 | -0.6 / 0.6 / 1.3 |
| undersea_3km_dip | baseline | -3.1 / 3.1 / 7.6 | -3.6 / 3.6 / 8.2 | -3.7 / 3.8 / 9.0 |
| undersea_3km_dip | ekf | -2.1 / 2.1 / 3.5 | -2.7 / 2.7 / 3.9 | -3.2 / 3.2 / 4.0 |
| undersea_3km_dip | ekf_zupt | -2.1 / 2.1 / 3.5 | -2.7 / 2.7 / 3.9 | -3.2 / 3.2 / 4.0 |
| undersea_3km_dip | pf | -2.4 / 2.4 / 3.8 | -3.1 / 3.1 / 4.3 | -3.5 / 3.5 / 4.6 |
