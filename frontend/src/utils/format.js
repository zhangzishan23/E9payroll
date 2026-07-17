export function isEmptyValue(val) {
  if (val == null) return true
  if (typeof val === 'number' && val === 0) return true
  if (typeof val === 'string' && val.trim() === '') return true
  return false
}

export function formatMoney(val) {
  if (isEmptyValue(val)) return ''
  return Number(val).toFixed(2)
}

export function formatNumber(val, decimals = null) {
  if (isEmptyValue(val)) return ''
  if (typeof val === 'number' && decimals != null) {
    return val.toFixed(decimals)
  }
  return val
}

export function formatInt(val) {
  if (isEmptyValue(val)) return ''
  return Math.round(Number(val))
}

export function formatPercent(val, decimals = 1) {
  if (isEmptyValue(val)) return ''
  return (Number(val) * 100).toFixed(decimals) + '%'
}

export function formatText(val) {
  if (val == null) return ''
  return String(val)
}
