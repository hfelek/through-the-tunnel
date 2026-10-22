# Side study: beacon_sigma

150 rows, commit 59d919a. `Runs` counts rows (vehicle x seed). Exit error is signed in the CSV; the table uses its absolute value (per tunnel where a scenario has several). Consistency is the share of tunnel samples with |error| < 2 sigma. Timing error is t - t_ideal (positive = late). Time per measurement was measured with several processes running in parallel, so only the ratios are meaningful.

## Accuracy

| Variant | Scenario | Estimator | Tunnel | Runs | Median abs. exit error (m) | p90 abs. exit error (m) | Median RMSE (m) | Mean consistency (%) | Missed callouts | Median time (µs/meas.) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sigma=10 | beacons_5km | ekf_zupt |  | 50 | 9.4 | 16.2 | 12.0 | 91.3 | 0 | 33.7 |
| sigma=15 | beacons_5km | ekf_zupt |  | 50 | 9.1 | 18.2 | 12.3 | 95.1 | 0 | 34.0 |
| sigma=5 | beacons_5km | ekf_zupt |  | 50 | 10.2 | 13.9 | 10.9 | 64.2 | 0 | 33.5 |

## Callout timing

| Variant | Scenario | Estimator | 500 m: median / median abs. / p90 abs. (s) | 200 m: median / median abs. / p90 abs. (s) | 0 m: median / median abs. / p90 abs. (s) |
| --- | --- | --- | --- | --- | --- |
| sigma=10 | beacons_5km | ekf_zupt | -0.1 / 0.2 / 0.5 | -0.1 / 0.1 / 0.6 | -0.3 / 0.3 / 0.8 |
| sigma=15 | beacons_5km | ekf_zupt | -0.2 / 0.3 / 0.7 | -0.2 / 0.3 / 0.7 | -0.5 / 0.5 / 0.9 |
| sigma=5 | beacons_5km | ekf_zupt | +0.1 / 0.2 / 0.3 | +0.2 / 0.2 / 0.4 | +0.0 / 0.2 / 0.4 |
