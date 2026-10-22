# Sensor presets

Two phone profiles. Every value in the JSON files carries its own `source` field; this page explains where the numbers come from and how the derived ones were computed.

Each file has an `id` (the file name, used in scenarios) and an optional `name`, the display name the UI shows ("High-end phone (2024)", "Low-cost phone"). A new preset needs a `name`, or the UI shows its id.

| Preset | Meaning | Basis |
| --- | --- | --- |
| `flagship_2024` | A current high-end smartphone | Bosch BMI260 (IMU marketed for smartphones) and BMP390 (barometer) datasheets, GPS.gov smartphone accuracy |
| `budget` | A low-cost smartphone | Flagship values scaled by 2–4× (assumption A16), since budget-phone sensor datasheets are rarely public |

The flagship preset is a representative smartphone-class IMU, not a specific phone. The BMI260 was chosen because Bosch markets it for smartphones and publishes its specifications. Teardowns show that the IMU market in phones is shared by STMicroelectronics, Bosch Sensortec and TDK InvenSense with specifications of the same order; iFixit identifies a Bosch Sensortec accelerometer and gyroscope in the iPhone 17 Pro, but not the exact part.

For comparison, STMicroelectronics' LSM6DSO (ST press release, 2018) lists 70 µg/√Hz accelerometer noise, 3.8 mdps/√Hz gyroscope noise and a typical ±1 dps zero-rate level: lower noise than the BMI260 but a larger gyroscope offset, all within a factor of two. Noise contributes only a few metres over a 3-minute tunnel and offsets are calibrated before the tunnel, so the choice between the two does not change the results; the BMI260 values are slightly conservative on noise.

## Which values matter most

For dead reckoning in a tunnel, a constant accelerometer bias `b` grows into a position error of `½·b·t²`. The factory bias (±20 mg ≈ 0.2 m/s²) would give kilometres of error, but it is estimated while GNSS is available before the tunnel. What remains is the **bias drift inside the tunnel**, so `bias_random_walk` is the value the results are most sensitive to. White noise only grows as `t^1.5` and contributes a few metres.

| Error source (flagship, 180 s tunnel) | Position error |
| --- | --- |
| Uncalibrated factory bias, 0.2 m/s² | ≈ 3 km |
| Residual bias after calibration, ≈ 0.005 m/s² | ≈ 80 m |
| Accelerometer white noise | ≈ 2 m |

## Unit conversions

- Accelerometer noise: 160 µg/√Hz × 9.80665 = 1.57 × 10⁻³ m/s²/√Hz
- Accelerometer offset: 20 mg × 9.80665 = 0.196 m/s²
- Gyroscope noise: 0.008 °/s/√Hz × π/180 = 1.40 × 10⁻⁴ rad/s/√Hz
- Gyroscope offset: 0.5 °/s × π/180 = 8.73 × 10⁻³ rad/s
- Barometer noise: 0.1 m altitude ≈ 1.2 Pa (about 12 Pa per metre near sea level)

## Derived drift values (assumption A14)

Datasheets give temperature coefficients rather than drift over time. Assuming the phone warms or cools by about 2 K during a 3-minute tunnel, the drift over 180 s is coefficient × 2 K, modelled as a random walk:

| Sensor | Temperature coefficient | Drift over 180 s | Random walk = drift / √180 |
| --- | --- | --- | --- |
| Accelerometer | 0.25 mg/K | 4.9 × 10⁻³ m/s² | 3.65 × 10⁻⁴ m/s²/√s |
| Gyroscope | 0.02 °/s/K | 6.98 × 10⁻⁴ rad/s | 5.20 × 10⁻⁵ rad/s/√s |
| Barometer | 0.6 Pa/K | 1.2 Pa | 0.089 Pa/√s |

## Assumed values (assumption A15)

Not taken from a datasheet: GNSS error correlation time (30 s), GNSS speed noise (0.15 m/s) and magnetometer noise (0.3 µT). The magnetometer is simulated only to show why it is unusable inside a tunnel.

## GNSS

GPS.gov states that GPS-enabled smartphones are typically accurate to within a 4.9 m radius under open sky. Treating that as a 95% horizontal radius gives about 2 m (1σ) per axis.

## Budget multipliers (assumption A16)

| Sensor | Multiplier |
| --- | --- |
| Accelerometer and gyroscope noise | 2× |
| Accelerometer offset | 2.5×; gyroscope offset 3× |
| Bias drift (all inertial sensors) | 3× |
| Scale error | 2.5× |
| Barometer noise | 4× (older generation, about ±1 m class) |
| Barometer drift | 3× |
| GNSS position and speed noise | 2× |
| Magnetometer noise | 2× |
