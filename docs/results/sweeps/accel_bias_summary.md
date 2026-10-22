# Sweep: accel_bias

1800 rows, commit 8e180c2. `Runs` counts rows (vehicle x seed). Exit error is signed in the CSV; the table uses its absolute value (per tunnel where a scenario has several). Consistency is the share of tunnel samples with |error| < 2 sigma. Timing error is t - t_ideal (positive = late). Time per measurement was measured with several processes running in parallel, so only the ratios are meaningful.

## Accuracy

Git hashes in the CSV: `8e180c2`

| Variant | Scenario | Estimator | Tunnel | Runs | Median abs. exit error (m) | p90 abs. exit error (m) | p95 abs. exit error (m) | Max abs. exit error (m) | Median RMSE (m) | Mean consistency (%) | Missed callouts | Median time (µs/meas.) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| x0.5 | curved_5km_exit_inside | baseline |  | 30 | 115.7 | 274.8 | 282.7 | 302.6 | 70.8 | 96.6 | 0 | 0.6 |
| x0.5 | curved_5km_exit_inside | ekf_zupt |  | 30 | 147.9 | 329.1 | 358.9 | 373.9 | 69.1 | 96.7 | 0 | 52.2 |
| x0.5 | curved_5km_exit_inside | pf |  | 30 | 15.7 | 32.2 | 48.6 | 57.8 | 12.0 | 97.4 | 0 | 70.8 |
| x0.5 | hard_brake_inside | baseline |  | 30 | 570.0 | 664.4 | 679.0 | 695.3 | 403.7 | 36.9 | 0 | 0.7 |
| x0.5 | hard_brake_inside | ekf_zupt |  | 30 | 6.1 | 19.9 | 24.5 | 29.6 | 5.1 | 84.7 | 0 | 55.8 |
| x0.5 | hard_brake_inside | pf |  | 30 | 6.5 | 20.1 | 23.2 | 28.9 | 5.8 | 93.7 | 0 | 73.4 |
| x0.5 | speed_changes_3km | baseline |  | 30 | 1012.5 | 1374.8 | 1491.4 | 1500.0 | 579.8 | 23.8 | 0 | 0.7 |
| x0.5 | speed_changes_3km | ekf_zupt |  | 30 | 77.6 | 150.3 | 175.0 | 186.8 | 35.0 | 96.7 | 0 | 54.2 |
| x0.5 | speed_changes_3km | pf |  | 30 | 83.4 | 164.1 | 184.9 | 195.3 | 34.5 | 97.0 | 0 | 72.9 |
| x0.5 | stop_and_go_3km | baseline |  | 30 | 1500.0 | 1500.0 | 1500.0 | 1500.0 | 1840.3 | 8.4 | 0 | 0.5 |
| x0.5 | stop_and_go_3km | ekf_zupt |  | 30 | 17.1 | 38.9 | 48.2 | 63.7 | 12.8 | 93.8 | 0 | 55.5 |
| x0.5 | stop_and_go_3km | pf |  | 30 | 25.3 | 43.5 | 45.1 | 92.6 | 14.1 | 99.0 | 0 | 80.9 |
| x1 | curved_5km_exit_inside | baseline |  | 30 | 115.7 | 274.8 | 282.7 | 302.6 | 70.8 | 96.6 | 0 | 0.6 |
| x1 | curved_5km_exit_inside | ekf_zupt |  | 30 | 172.4 | 334.8 | 354.6 | 385.7 | 83.3 | 96.7 | 0 | 53.1 |
| x1 | curved_5km_exit_inside | pf |  | 30 | 22.1 | 57.8 | 64.1 | 66.8 | 12.6 | 97.4 | 0 | 72.2 |
| x1 | hard_brake_inside | baseline |  | 30 | 570.0 | 664.4 | 679.0 | 695.3 | 403.7 | 36.9 | 0 | 0.7 |
| x1 | hard_brake_inside | ekf_zupt |  | 30 | 5.8 | 19.5 | 23.8 | 29.5 | 4.6 | 85.0 | 0 | 55.3 |
| x1 | hard_brake_inside | pf |  | 30 | 5.4 | 19.7 | 22.3 | 28.7 | 4.9 | 93.8 | 0 | 72.2 |
| x1 | speed_changes_3km | baseline |  | 30 | 1012.5 | 1374.8 | 1491.4 | 1500.0 | 579.8 | 23.8 | 0 | 0.7 |
| x1 | speed_changes_3km | ekf_zupt |  | 30 | 75.1 | 172.3 | 214.1 | 265.3 | 34.2 | 95.8 | 0 | 54.0 |
| x1 | speed_changes_3km | pf |  | 30 | 78.7 | 169.6 | 224.0 | 273.8 | 34.1 | 96.9 | 0 | 70.9 |
| x1 | stop_and_go_3km | baseline |  | 30 | 1500.0 | 1500.0 | 1500.0 | 1500.0 | 1840.3 | 8.4 | 0 | 0.6 |
| x1 | stop_and_go_3km | ekf_zupt |  | 30 | 17.3 | 43.5 | 48.2 | 75.9 | 14.1 | 90.4 | 0 | 56.7 |
| x1 | stop_and_go_3km | pf |  | 30 | 26.9 | 45.0 | 45.6 | 103.2 | 15.1 | 99.0 | 0 | 87.5 |
| x2 | curved_5km_exit_inside | baseline |  | 30 | 115.7 | 274.8 | 282.7 | 302.6 | 70.8 | 96.6 | 0 | 0.6 |
| x2 | curved_5km_exit_inside | ekf_zupt |  | 30 | 227.1 | 432.0 | 454.9 | 515.7 | 106.5 | 96.8 | 0 | 53.1 |
| x2 | curved_5km_exit_inside | pf |  | 30 | 23.5 | 69.0 | 82.8 | 90.8 | 14.1 | 97.3 | 0 | 71.8 |
| x2 | hard_brake_inside | baseline |  | 30 | 570.0 | 664.4 | 679.0 | 695.3 | 403.7 | 36.9 | 0 | 0.7 |
| x2 | hard_brake_inside | ekf_zupt |  | 30 | 7.6 | 17.0 | 22.4 | 29.2 | 5.3 | 87.7 | 0 | 55.1 |
| x2 | hard_brake_inside | pf |  | 30 | 6.2 | 16.7 | 22.0 | 28.3 | 4.6 | 93.9 | 0 | 72.2 |
| x2 | speed_changes_3km | baseline |  | 30 | 1012.5 | 1374.8 | 1491.4 | 1500.0 | 579.8 | 23.8 | 0 | 0.8 |
| x2 | speed_changes_3km | ekf_zupt |  | 30 | 91.7 | 249.3 | 316.8 | 422.4 | 37.0 | 92.1 | 0 | 61.6 |
| x2 | speed_changes_3km | pf |  | 30 | 97.0 | 244.8 | 315.1 | 430.8 | 36.8 | 92.6 | 0 | 79.6 |
| x2 | stop_and_go_3km | baseline |  | 30 | 1500.0 | 1500.0 | 1500.0 | 1500.0 | 1840.3 | 8.4 | 0 | 0.5 |
| x2 | stop_and_go_3km | ekf_zupt |  | 30 | 19.2 | 52.0 | 57.4 | 99.5 | 17.2 | 88.0 | 0 | 51.9 |
| x2 | stop_and_go_3km | pf |  | 30 | 26.2 | 45.8 | 54.2 | 121.8 | 15.6 | 98.8 | 0 | 74.5 |
| x3 | curved_5km_exit_inside | baseline |  | 30 | 115.7 | 274.8 | 282.7 | 302.6 | 70.8 | 96.6 | 0 | 0.6 |
| x3 | curved_5km_exit_inside | ekf_zupt |  | 30 | 240.0 | 535.2 | 570.6 | 686.0 | 110.4 | 95.9 | 0 | 53.0 |
| x3 | curved_5km_exit_inside | pf |  | 30 | 36.2 | 92.9 | 99.5 | 128.6 | 15.3 | 96.7 | 0 | 71.6 |
| x3 | hard_brake_inside | baseline |  | 30 | 570.0 | 664.4 | 679.0 | 695.3 | 403.7 | 36.9 | 0 | 0.7 |
| x3 | hard_brake_inside | ekf_zupt |  | 30 | 9.6 | 19.5 | 27.8 | 29.8 | 7.2 | 86.9 | 0 | 55.9 |
| x3 | hard_brake_inside | pf |  | 30 | 8.1 | 20.1 | 26.0 | 28.0 | 6.0 | 94.3 | 0 | 72.4 |
| x3 | speed_changes_3km | baseline |  | 30 | 1012.5 | 1374.8 | 1491.4 | 1500.0 | 579.8 | 23.8 | 0 | 0.7 |
| x3 | speed_changes_3km | ekf_zupt |  | 30 | 124.2 | 329.5 | 432.9 | 579.6 | 55.2 | 84.6 | 0 | 56.8 |
| x3 | speed_changes_3km | pf |  | 30 | 127.3 | 324.2 | 431.2 | 587.9 | 55.0 | 90.0 | 0 | 83.8 |
| x3 | stop_and_go_3km | baseline |  | 30 | 1500.0 | 1500.0 | 1500.0 | 1500.0 | 1840.3 | 8.4 | 0 | 0.5 |
| x3 | stop_and_go_3km | ekf_zupt |  | 30 | 25.7 | 76.1 | 210.4 | 1360.8 | 21.6 | 80.8 | 0 | 52.1 |
| x3 | stop_and_go_3km | pf |  | 30 | 28.3 | 67.3 | 227.5 | 1498.3 | 17.9 | 95.6 | 0 | 76.0 |
| x5 | curved_5km_exit_inside | baseline |  | 30 | 115.7 | 274.8 | 282.7 | 302.6 | 70.8 | 96.6 | 0 | 0.6 |
| x5 | curved_5km_exit_inside | ekf_zupt |  | 30 | 378.6 | 850.3 | 877.9 | 1025.9 | 157.1 | 89.1 | 0 | 58.6 |
| x5 | curved_5km_exit_inside | pf |  | 30 | 62.1 | 141.0 | 154.1 | 160.0 | 21.9 | 93.4 | 0 | 79.7 |
| x5 | hard_brake_inside | baseline |  | 30 | 570.0 | 664.4 | 679.0 | 695.3 | 403.7 | 36.9 | 0 | 0.7 |
| x5 | hard_brake_inside | ekf_zupt |  | 30 | 12.7 | 27.3 | 31.1 | 88.6 | 9.5 | 85.2 | 0 | 55.1 |
| x5 | hard_brake_inside | pf |  | 30 | 12.5 | 26.0 | 30.1 | 87.5 | 8.9 | 94.1 | 0 | 72.1 |
| x5 | speed_changes_3km | baseline |  | 30 | 1012.5 | 1374.8 | 1491.4 | 1500.0 | 579.8 | 23.8 | 0 | 0.7 |
| x5 | speed_changes_3km | ekf_zupt |  | 30 | 228.4 | 491.5 | 667.2 | 677.8 | 93.1 | 72.1 | 0 | 56.2 |
| x5 | speed_changes_3km | pf |  | 30 | 229.3 | 497.2 | 666.4 | 900.8 | 92.9 | 75.6 | 0 | 74.6 |
| x5 | stop_and_go_3km | baseline |  | 30 | 1500.0 | 1500.0 | 1500.0 | 1500.0 | 1840.3 | 8.4 | 0 | 0.5 |
| x5 | stop_and_go_3km | ekf_zupt |  | 30 | 52.3 | 264.8 | 387.8 | 972.1 | 42.2 | 61.7 | 0 | 51.4 |
| x5 | stop_and_go_3km | pf |  | 30 | 48.4 | 275.8 | 406.0 | 1500.0 | 32.8 | 93.4 | 0 | 74.4 |

## Callout timing

Git hashes in the CSV: `8e180c2`

| Variant | Scenario | Estimator | 500 m: median / median abs. / p90 abs. (s) | 200 m: median / median abs. / p90 abs. (s) | 0 m: median / median abs. / p90 abs. (s) |
| --- | --- | --- | --- | --- | --- |
| x0.5 | curved_5km_exit_inside | baseline | -8.2 / 8.2 / 14.7 | -8.8 / 8.8 / 16.0 | -9.3 / 9.3 / 16.7 |
| x0.5 | curved_5km_exit_inside | ekf_zupt | -13.3 / 13.3 / 20.7 | -14.1 / 14.1 / 21.4 | -14.3 / 14.3 / 22.2 |
| x0.5 | curved_5km_exit_inside | pf | -0.5 / 0.5 / 0.6 | -1.1 / 1.1 / 1.6 | -1.7 / 1.7 / 2.3 |
| x0.5 | hard_brake_inside | baseline | -27.6 / 27.6 / 29.2 | -27.9 / 27.9 / 29.7 | -27.9 / 27.9 / 30.3 |
| x0.5 | hard_brake_inside | ekf_zupt | -0.5 / 0.5 / 1.1 | -0.5 / 0.5 / 1.2 | -0.5 / 0.5 / 1.2 |
| x0.5 | hard_brake_inside | pf | -1.3 / 1.3 / 2.0 | -1.6 / 1.6 / 2.3 | -1.9 / 1.9 / 2.5 |
| x0.5 | speed_changes_3km | baseline | -48.8 / 48.8 / 57.8 | -51.5 / 51.5 / 61.7 | -53.4 / 53.4 / 64.9 |
| x0.5 | speed_changes_3km | ekf_zupt | -4.3 / 4.3 / 10.1 | -5.9 / 5.9 / 11.3 | -6.6 / 6.6 / 13.2 |
| x0.5 | speed_changes_3km | pf | -4.9 / 4.9 / 11.2 | -6.4 / 6.4 / 12.2 | -7.1 / 7.1 / 13.8 |
| x0.5 | stop_and_go_3km | baseline | -227.1 / 227.1 / 257.7 | -275.2 / 275.2 / 296.5 | -284.5 / 284.5 / 301.0 |
| x0.5 | stop_and_go_3km | ekf_zupt | -1.3 / 2.0 / 4.4 | -1.2 / 2.2 / 3.7 | -0.4 / 1.0 / 1.9 |
| x0.5 | stop_and_go_3km | pf | -46.5 / 46.5 / 55.9 | -54.1 / 54.1 / 67.4 | -28.7 / 28.7 / 58.1 |
| x1 | curved_5km_exit_inside | baseline | -8.2 / 8.2 / 14.7 | -8.8 / 8.8 / 16.0 | -9.3 / 9.3 / 16.7 |
| x1 | curved_5km_exit_inside | ekf_zupt | -13.6 / 13.6 / 20.9 | -13.8 / 13.8 / 21.8 | -13.8 / 13.8 / 22.3 |
| x1 | curved_5km_exit_inside | pf | -0.4 / 0.4 / 0.6 | -1.2 / 1.2 / 1.6 | -1.7 / 1.7 / 2.4 |
| x1 | hard_brake_inside | baseline | -27.6 / 27.6 / 29.2 | -27.9 / 27.9 / 29.7 | -27.9 / 27.9 / 30.3 |
| x1 | hard_brake_inside | ekf_zupt | -0.5 / 0.5 / 1.1 | -0.5 / 0.5 / 1.2 | -0.4 / 0.4 / 1.2 |
| x1 | hard_brake_inside | pf | -1.3 / 1.3 / 2.0 | -1.6 / 1.6 / 2.3 | -1.9 / 1.9 / 2.5 |
| x1 | speed_changes_3km | baseline | -48.8 / 48.8 / 57.8 | -51.5 / 51.5 / 61.7 | -53.4 / 53.4 / 64.9 |
| x1 | speed_changes_3km | ekf_zupt | -4.1 / 4.1 / 9.0 | -5.8 / 5.8 / 10.5 | -6.2 / 6.2 / 12.1 |
| x1 | speed_changes_3km | pf | -4.8 / 4.8 / 10.0 | -6.3 / 6.3 / 11.2 | -7.0 / 7.0 / 13.1 |
| x1 | stop_and_go_3km | baseline | -227.1 / 227.1 / 257.7 | -275.2 / 275.2 / 296.5 | -284.5 / 284.5 / 301.0 |
| x1 | stop_and_go_3km | ekf_zupt | -1.2 / 2.3 / 6.0 | -1.3 / 2.5 / 4.2 | -0.6 / 1.0 / 1.9 |
| x1 | stop_and_go_3km | pf | -46.0 / 46.0 / 55.2 | -54.2 / 54.2 / 66.9 | -30.1 / 30.1 / 57.4 |
| x2 | curved_5km_exit_inside | baseline | -8.2 / 8.2 / 14.7 | -8.8 / 8.8 / 16.0 | -9.3 / 9.3 / 16.7 |
| x2 | curved_5km_exit_inside | ekf_zupt | -12.9 / 12.9 / 20.6 | -12.6 / 12.6 / 21.0 | -13.0 / 13.0 / 21.4 |
| x2 | curved_5km_exit_inside | pf | -0.3 / 0.3 / 0.7 | -1.0 / 1.0 / 1.6 | -1.5 / 1.5 / 2.3 |
| x2 | hard_brake_inside | baseline | -27.6 / 27.6 / 29.2 | -27.9 / 27.9 / 29.7 | -27.9 / 27.9 / 30.3 |
| x2 | hard_brake_inside | ekf_zupt | -0.5 / 0.5 / 1.1 | -0.5 / 0.5 / 1.2 | -0.5 / 0.5 / 1.2 |
| x2 | hard_brake_inside | pf | -1.3 / 1.3 / 2.0 | -1.6 / 1.6 / 2.3 | -1.8 / 1.8 / 2.5 |
| x2 | speed_changes_3km | baseline | -48.8 / 48.8 / 57.8 | -51.5 / 51.5 / 61.7 | -53.4 / 53.4 / 64.9 |
| x2 | speed_changes_3km | ekf_zupt | -4.8 / 4.8 / 9.6 | -5.5 / 6.1 / 11.4 | -6.5 / 6.7 / 13.0 |
| x2 | speed_changes_3km | pf | -5.3 / 5.3 / 10.3 | -6.5 / 6.5 / 12.1 | -7.0 / 7.0 / 13.6 |
| x2 | stop_and_go_3km | baseline | -227.1 / 227.1 / 257.7 | -275.2 / 275.2 / 296.5 | -284.5 / 284.5 / 301.0 |
| x2 | stop_and_go_3km | ekf_zupt | -1.1 / 2.6 / 7.7 | -1.1 / 2.5 / 5.0 | -0.4 / 1.3 / 2.4 |
| x2 | stop_and_go_3km | pf | -47.8 / 47.8 / 54.9 | -54.1 / 54.1 / 66.3 | -30.2 / 30.2 / 57.6 |
| x3 | curved_5km_exit_inside | baseline | -8.2 / 8.2 / 14.7 | -8.8 / 8.8 / 16.0 | -9.3 / 9.3 / 16.7 |
| x3 | curved_5km_exit_inside | ekf_zupt | -13.5 / 13.5 / 21.2 | -13.5 / 14.0 / 22.4 | -13.9 / 15.7 / 22.2 |
| x3 | curved_5km_exit_inside | pf | -0.4 / 0.4 / 0.7 | -1.0 / 1.0 / 1.8 | -1.5 / 1.6 / 2.5 |
| x3 | hard_brake_inside | baseline | -27.6 / 27.6 / 29.2 | -27.9 / 27.9 / 29.7 | -27.9 / 27.9 / 30.3 |
| x3 | hard_brake_inside | ekf_zupt | -0.5 / 0.5 / 1.1 | -0.5 / 0.5 / 1.2 | -0.5 / 0.5 / 1.1 |
| x3 | hard_brake_inside | pf | -1.4 / 1.4 / 2.0 | -1.7 / 1.7 / 2.3 | -1.8 / 1.8 / 2.5 |
| x3 | speed_changes_3km | baseline | -48.8 / 48.8 / 57.8 | -51.5 / 51.5 / 61.7 | -53.4 / 53.4 / 64.9 |
| x3 | speed_changes_3km | ekf_zupt | -4.1 / 5.7 / 12.0 | -5.6 / 6.9 / 13.8 | -6.2 / 7.5 / 15.7 |
| x3 | speed_changes_3km | pf | -4.9 / 5.4 / 12.8 | -6.4 / 7.3 / 14.3 | -7.1 / 8.0 / 15.8 |
| x3 | stop_and_go_3km | baseline | -227.1 / 227.1 / 257.7 | -275.2 / 275.2 / 296.5 | -284.5 / 284.5 / 301.0 |
| x3 | stop_and_go_3km | ekf_zupt | -0.5 / 3.0 / 30.9 | -0.7 / 2.8 / 7.6 | -0.2 / 1.4 / 3.0 |
| x3 | stop_and_go_3km | pf | -48.0 / 48.0 / 56.7 | -52.8 / 52.8 / 68.9 | -32.4 / 32.4 / 58.0 |
| x5 | curved_5km_exit_inside | baseline | -8.2 / 8.2 / 14.7 | -8.8 / 8.8 / 16.0 | -9.3 / 9.3 / 16.7 |
| x5 | curved_5km_exit_inside | ekf_zupt | -13.8 / 15.8 / 23.8 | -13.9 / 16.7 / 25.6 | -13.7 / 17.9 / 28.9 |
| x5 | curved_5km_exit_inside | pf | -0.4 / 0.4 / 0.7 | -0.9 / 1.1 / 2.1 | -1.3 / 1.7 / 3.2 |
| x5 | hard_brake_inside | baseline | -27.6 / 27.6 / 29.2 | -27.9 / 27.9 / 29.7 | -27.9 / 27.9 / 30.3 |
| x5 | hard_brake_inside | ekf_zupt | -0.6 / 0.6 / 1.1 | -0.5 / 0.6 / 1.2 | -0.5 / 0.5 / 1.3 |
| x5 | hard_brake_inside | pf | -1.5 / 1.5 / 1.9 | -1.7 / 1.7 / 2.3 | -1.8 / 1.8 / 2.6 |
| x5 | speed_changes_3km | baseline | -48.8 / 48.8 / 57.8 | -51.5 / 51.5 / 61.7 | -53.4 / 53.4 / 64.9 |
| x5 | speed_changes_3km | ekf_zupt | -3.9 / 8.6 / 18.5 | -4.7 / 10.6 / 19.4 | -5.1 / 11.6 / 21.8 |
| x5 | speed_changes_3km | pf | -4.6 / 9.1 / 19.4 | -5.6 / 11.2 / 20.3 | -6.2 / 12.3 / 22.7 |
| x5 | stop_and_go_3km | baseline | -227.1 / 227.1 / 257.7 | -275.2 / 275.2 / 296.5 | -284.5 / 284.5 / 301.0 |
| x5 | stop_and_go_3km | ekf_zupt | -0.7 / 5.8 / 44.0 | -0.9 / 5.3 / 27.4 | -0.2 / 3.0 / 13.7 |
| x5 | stop_and_go_3km | pf | -46.7 / 46.7 / 59.9 | -52.4 / 52.4 / 69.9 | -36.7 / 36.7 / 60.1 |
