export const GNSS_GAP_S = 1.5 // fixes further apart than this are an outage; the line must break

const col = (m, k) => m?.[k] ?? null

/** Rows {t, ...keys} from columnar arrays; `fns` maps an output key to (i) => value. */
function rows(m, fns) {
  return m.t.map((t, i) => {
    const r = { t }
    for (const [k, f] of Object.entries(fns)) r[k] = f(i)
    return r
  })
}

/** Inserts a null row inside every gap longer than `gap` so Recharts breaks the line there. */
export function breakGaps(data, keys, gap = GNSS_GAP_S) {
  const out = []
  data.forEach((r, i) => {
    if (i > 0 && r.t - data[i - 1].t > gap) {
      const hole = { t: (r.t + data[i - 1].t) / 2 }
      for (const k of keys) hole[k] = null
      out.push(hole)
    }
    out.push(r)
  })
  return out
}

const BLUE = '#2563eb'
const RED = '#dc2626'
const GREEN = '#059669'

/** Chart specs for the sensors present in a vehicle's measurements (a missing sensor has no chart). */
export function buildCharts(vehicle) {
  const m = vehicle?.measurements ?? {}
  const charts = []
  const imu = m.imu
  if (imu?.t?.length) {
    const axes = (keys) => Object.fromEntries(keys.map((k) => [k, (i) => imu[k][i]]))
    charts.push({
      id: 'accel', title: 'Accelerometer (raw phone axes)', unit: 'm/s²', type: 'line', data: rows(imu, axes(['ax', 'ay', 'az'])),
      series: [{ key: 'ax', color: BLUE }, { key: 'ay', color: RED }, { key: 'az', color: GREEN }],
    })
    charts.push({
      id: 'gyro', title: 'Gyroscope', unit: 'rad/s', type: 'line', data: rows(imu, axes(['gx', 'gy', 'gz'])),
      series: [{ key: 'gx', color: BLUE }, { key: 'gy', color: RED }, { key: 'gz', color: GREEN }],
    })
  }
  if (m.baro?.t?.length) {
    charts.push({
      id: 'baro', title: 'Barometer', unit: 'hPa', type: 'line', data: rows(m.baro, { p: (i) => m.baro.p_hpa[i] }),
      series: [{ key: 'p', color: BLUE }],
    })
  }
  const g = m.gnss
  if (g?.t?.length) {
    const keys = ['h_acc', 'speed_kmh']
    const data = breakGaps(rows(g, { h_acc: (i) => g.h_acc[i], speed_kmh: (i) => g.speed[i] * 3.6 }), keys)
    charts.push({ id: 'gnss_acc', title: 'GNSS horizontal accuracy', unit: 'm', type: 'line', data, series: [{ key: 'h_acc', color: RED }] })
    charts.push({ id: 'gnss_speed', title: 'GNSS speed', unit: 'km/h', type: 'line', data, series: [{ key: 'speed_kmh', color: BLUE }] })
  }
  const mag = m.mag
  if (mag?.t?.length) {
    charts.push({
      id: 'mag', title: 'Magnetometer |B|', unit: 'µT', type: 'line',
      data: rows(mag, { b: (i) => Math.hypot(mag.mx[i], mag.my[i], mag.mz[i]) }), series: [{ key: 'b', color: BLUE }],
    })
  }
  const ble = m.ble
  if (ble?.t?.length) {
    const by = new Map()
    ble.t.forEach((t, i) => {
      const id = String(col(ble, 'beacon_id')[i])
      if (!by.has(id)) by.set(id, [])
      by.get(id).push({ t, rssi: ble.rssi[i] })
    })
    const ids = [...by.keys()].sort()
    charts.push({
      id: 'ble', title: 'BLE RSSI (one color per beacon)', unit: 'dBm', type: 'scatter',
      series: ids.map((id, k) => ({ key: id, data: by.get(id), color: BEACON_COLORS[k % BEACON_COLORS.length] })),
    })
  }
  return charts
}

const BEACON_COLORS = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2', '#db2777', '#65a30d']
