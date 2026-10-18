/** Index of the first element >= x in a sorted array (arr.length if none). */
export function lowerBound(arr, x) {
  let lo = 0
  let hi = arr.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (arr[mid] < x) lo = mid + 1
    else hi = mid
  }
  return lo
}

/** Linear interpolation of values over sorted times; clamps outside the range. */
export function interpAt(tArr, vArr, t) {
  const n = tArr.length
  if (n === 0) return undefined
  if (t <= tArr[0]) return vArr[0]
  if (t >= tArr[n - 1]) return vArr[n - 1]
  const i = lowerBound(tArr, t)
  const f = (t - tArr[i - 1]) / (tArr[i] - tArr[i - 1])
  return vArr[i - 1] + f * (vArr[i] - vArr[i - 1])
}
