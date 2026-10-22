# Side study: a30

300 rows, commit f191672. `Runs` counts rows (vehicle x seed). Exit error is signed in the CSV; the table uses its absolute value (per tunnel where a scenario has several). Consistency is the share of tunnel samples with |error| < 2 sigma. Timing error is t - t_ideal (positive = late). Time per measurement was measured with several processes running in parallel, so only the ratios are meaningful.

## Accuracy

Git hashes in the CSV: `f191672`

| Variant | Scenario | Estimator | Tunnel | Runs | Median abs. exit error (m) | p90 abs. exit error (m) | p95 abs. exit error (m) | Max abs. exit error (m) | Median RMSE (m) | Mean consistency (%) | Missed callouts | Median time (µs/meas.) | Mean accelerometer use after put-back (%) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c1=0.02 | phone_handled_mid_tunnel | ekf_zupt |  | 50 | 46.2 | 117.7 | 125.5 | 159.9 | 22.7 | 95.0 | 0 | 52.2 | 0.0 |
| c1=0.02 | phone_in_hand_2min | ekf_zupt |  | 50 | 101.6 | 220.9 | 244.1 | 326.3 | 56.2 | 97.6 | 0 | 62.2 | 0.0 |
| c1=0.03 | phone_handled_mid_tunnel | ekf_zupt |  | 50 | 46.2 | 117.7 | 125.5 | 159.9 | 22.7 | 95.0 | 0 | 52.7 | 0.0 |
| c1=0.03 | phone_in_hand_2min | ekf_zupt |  | 50 | 101.6 | 220.9 | 244.1 | 326.3 | 56.2 | 97.6 | 0 | 74.4 | 0.0 |
| c1=1e-9 | phone_handled_mid_tunnel | ekf_zupt |  | 50 | 108.0 | 296.1 | 319.1 | 422.8 | 36.5 | 92.1 | 0 | 52.3 | 100.0 |
| c1=1e-9 | phone_in_hand_2min | ekf_zupt |  | 50 | 785.7 | 1890.7 | 1899.3 | 2130.4 | 303.8 | 87.2 | 0 | 60.3 | 100.0 |

## Callout timing

Git hashes in the CSV: `f191672`

| Variant | Scenario | Estimator | 500 m: median / median abs. / p90 abs. (s) | 200 m: median / median abs. / p90 abs. (s) | 0 m: median / median abs. / p90 abs. (s) |
| --- | --- | --- | --- | --- | --- |
| c1=0.02 | phone_handled_mid_tunnel | ekf_zupt | -2.1 / 2.2 / 3.8 | -3.3 / 3.3 / 5.3 | -4.2 / 4.2 / 6.2 |
| c1=0.02 | phone_in_hand_2min | ekf_zupt | -19.3 / 19.3 / 24.5 | -21.6 / 21.6 / 27.2 | -23.1 / 23.1 / 29.0 |
| c1=0.03 | phone_handled_mid_tunnel | ekf_zupt | -2.1 / 2.2 / 3.8 | -3.3 / 3.3 / 5.3 | -4.2 / 4.2 / 6.2 |
| c1=0.03 | phone_in_hand_2min | ekf_zupt | -19.3 / 19.3 / 24.5 | -21.6 / 21.6 / 27.2 | -23.1 / 23.1 / 29.0 |
| c1=1e-9 | phone_handled_mid_tunnel | ekf_zupt | -2.0 / 2.1 / 3.8 | -2.8 / 3.2 / 6.1 | -3.7 / 4.1 / 8.1 |
| c1=1e-9 | phone_in_hand_2min | ekf_zupt | +0.6 / 20.7 / 63.1 | -2.2 / 25.9 / 47.9 | -5.6 / 29.3 / 37.7 |
