# Sweep: tunnel_length

600 rows, commit 8e180c2. `Runs` counts rows (vehicle x seed). Exit error is signed in the CSV; the table uses its absolute value (per tunnel where a scenario has several). Consistency is the share of tunnel samples with |error| < 2 sigma. Timing error is t - t_ideal (positive = late). Time per measurement was measured with several processes running in parallel, so only the ratios are meaningful.

## Accuracy

Git hashes in the CSV: `8e180c2`

| Variant | Scenario | Estimator | Tunnel | Runs | Median abs. exit error (m) | p90 abs. exit error (m) | p95 abs. exit error (m) | Max abs. exit error (m) | Median RMSE (m) | Mean consistency (%) | Missed callouts | Median time (µs/meas.) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5 km | short_straight_500m | baseline |  | 30 | 13.3 | 26.0 | 30.7 | 36.7 | 11.0 | 99.3 | – | 1.0 |
| 0.5 km | short_straight_500m | ekf |  | 30 | 2.5 | 6.3 | 9.8 | 13.9 | 1.6 | 78.9 | – | 56.4 |
| 0.5 km | short_straight_500m | ekf_zupt |  | 30 | 2.5 | 6.3 | 9.8 | 13.9 | 1.6 | 78.9 | – | 61.6 |
| 0.5 km | short_straight_500m | pf |  | 30 | 2.6 | 6.1 | 9.5 | 13.8 | 1.6 | 82.0 | – | 73.0 |
| 1 km | short_straight_500m | baseline |  | 30 | 23.2 | 48.1 | 49.9 | 56.4 | 16.0 | 99.6 | – | 0.9 |
| 1 km | short_straight_500m | ekf |  | 30 | 9.0 | 18.3 | 19.6 | 20.6 | 4.4 | 89.8 | – | 55.1 |
| 1 km | short_straight_500m | ekf_zupt |  | 30 | 9.0 | 18.3 | 19.6 | 20.6 | 4.4 | 89.8 | – | 58.1 |
| 1 km | short_straight_500m | pf |  | 30 | 9.3 | 18.7 | 20.1 | 21.9 | 4.3 | 92.2 | – | 72.5 |
| 2 km | short_straight_500m | baseline |  | 30 | 42.7 | 85.3 | 96.8 | 133.9 | 27.5 | 98.8 | – | 0.8 |
| 2 km | short_straight_500m | ekf |  | 30 | 18.6 | 77.3 | 83.0 | 122.2 | 10.7 | 87.5 | – | 52.5 |
| 2 km | short_straight_500m | ekf_zupt |  | 30 | 18.6 | 77.3 | 83.0 | 122.2 | 10.7 | 87.5 | – | 55.8 |
| 2 km | short_straight_500m | pf |  | 30 | 20.0 | 78.0 | 83.6 | 121.6 | 11.0 | 92.8 | – | 72.4 |
| 3 km | short_straight_500m | baseline |  | 30 | 63.9 | 137.3 | 152.9 | 187.6 | 37.5 | 98.4 | – | 0.7 |
| 3 km | short_straight_500m | ekf |  | 30 | 53.9 | 140.0 | 162.6 | 218.7 | 23.0 | 89.9 | – | 51.1 |
| 3 km | short_straight_500m | ekf_zupt |  | 30 | 53.9 | 140.0 | 162.6 | 218.7 | 23.0 | 89.9 | – | 54.4 |
| 3 km | short_straight_500m | pf |  | 30 | 57.6 | 143.9 | 164.7 | 219.2 | 24.4 | 95.5 | – | 71.7 |
| 5 km | short_straight_500m | baseline |  | 30 | 89.1 | 222.9 | 271.9 | 346.7 | 53.2 | 96.7 | – | 0.6 |
| 5 km | short_straight_500m | ekf |  | 30 | 167.4 | 358.7 | 430.4 | 798.7 | 74.7 | 93.2 | – | 48.1 |
| 5 km | short_straight_500m | ekf_zupt |  | 30 | 167.4 | 358.7 | 430.4 | 798.7 | 74.7 | 93.2 | – | 51.4 |
| 5 km | short_straight_500m | pf |  | 30 | 171.3 | 336.6 | 432.3 | 801.0 | 76.3 | 95.6 | – | 71.6 |

## Callout timing

Git hashes in the CSV: `8e180c2`

| Variant | Scenario | Estimator | 500 m: median / median abs. / p90 abs. (s) | 200 m: median / median abs. / p90 abs. (s) | 0 m: median / median abs. / p90 abs. (s) |
| --- | --- | --- | --- | --- | --- |
