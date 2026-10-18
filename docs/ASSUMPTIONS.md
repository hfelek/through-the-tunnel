# Assumptions

Numbered assumptions. Code that depends on one references it with a comment (`# A7`). New assumptions get the next number; never renumber.

- **A1** Tunnel is single-lane, no overtaking; the vehicle's route is known from navigation.
- **A2** Map centerline, curvature and grade are accurate (error < 2 m).
- **A3** Phone is fixed in a mount; taking it out of the mount is modeled as a separate scenario.
- **A4** There are at least 60 s of good GNSS before the tunnel (calibration window).
- **A5** Sensors: accelerometer, gyroscope, magnetometer, barometer, GNSS. No vehicle speed data (OBD, CarPlay); discussed as "what if" in the write-up.
- **A6** No GNSS, cellular or Wi-Fi positioning inside the tunnel.
- **A7** Beacons exist only in scenarios that explicitly enable them.
- **A8** In simulation, sensor timestamps are synchronized and delay-free.
- **A9** The callout point is where the exit on the route begins; the driver does not miss the exit.
- **A10** With several vehicles, the single lane means a follower cannot get closer than a minimum gap to the vehicle ahead.
- **A11** Longitudinal motion is jerk-limited at 2.0 m/s³. Speed changes the scenario gives no acceleration for (cruise to a new speed, `stop_and_go`) use 1.5 m/s². Both are typical passenger-comfort bounds (e.g. Hoberock 1977, "A survey of longitudinal acceleration comfort studies in ground transportation vehicles").
- **A12** Pitch is blended over 40 m (`VERTICAL_BLEND_M`) at grade changes, like road vertical curves, so the vertical acceleration `v² · d(pitch)/ds` has no spikes at grade steps.
