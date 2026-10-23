# Side study: beacon_sigma

150 rows, commit f191672. `Runs` counts rows (vehicle x seed). Exit error is signed in the CSV; the table uses its absolute value (per tunnel where a scenario has several). Consistency is the share of tunnel samples with |error| < 2 sigma. Timing error is t - t_ideal (positive = late). Time per measurement was measured with several processes running in parallel, so only the ratios are meaningful.

## Accuracy

Git hashes in the CSV: `f191672`

| Variant | Scenario | Estimator | Tunnel | Runs | Median abs. exit error (m) | p90 abs. exit error (m) | p95 abs. exit error (m) | Max abs. exit error (m) | Median recovery (s) | p90 recovery (s) | Not recovered | Median max display jump (m) | Max display jump (m) | Median RMSE (m) | Mean consistency (%) | Missed callouts | Median time (µs/meas.) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sigma=10 | beacons_5km | ekf_zupt |  | 50 | 2.9 | 9.1 | 15.9 | 102.5 | – | – | 0 | – | – | 5.4 | 96.5 | 0 | 53.0 |
| sigma=15 | beacons_5km | ekf_zupt |  | 50 | 4.5 | 10.6 | 13.0 | 23.2 | – | – | 0 | – | – | 6.8 | 96.9 | 0 | 53.6 |
| sigma=5 | beacons_5km | ekf_zupt |  | 50 | 2.7 | 6.8 | 7.0 | 17.2 | – | – | 0 | – | – | 3.8 | 97.2 | 0 | 52.7 |

## Callout timing

Git hashes in the CSV: `f191672`

| Variant | Scenario | Estimator | 500 m: median / median abs. / p90 abs. (s) | 200 m: median / median abs. / p90 abs. (s) | 0 m: median / median abs. / p90 abs. (s) |
| --- | --- | --- | --- | --- | --- |
| sigma=10 | beacons_5km | ekf_zupt | -0.6 / 0.6 / 0.9 | -0.5 / 0.5 / 0.8 | -0.7 / 0.7 / 1.0 |
| sigma=15 | beacons_5km | ekf_zupt | -0.7 / 0.7 / 1.2 | -0.7 / 0.7 / 1.1 | -1.0 / 1.0 / 1.4 |
| sigma=5 | beacons_5km | ekf_zupt | -0.3 / 0.3 / 0.5 | -0.3 / 0.3 / 0.5 | -0.4 / 0.4 / 0.7 |
