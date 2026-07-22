const routePrefix = import.meta.env.VITE_ROUTE_PREFIX || ''
const normalizedPrefix = routePrefix
  ? (routePrefix.startsWith('/') ? routePrefix : '/' + routePrefix).replace(/\/$/, '')
  : ''

export function withPrefix(path) {
  if (!path) return path
  if (normalizedPrefix) {
    return path.startsWith('/') ? `${normalizedPrefix}${path}` : `${normalizedPrefix}/${path}`
  }
  return path.startsWith('/') ? path : `/${path}`
}

export { normalizedPrefix as routePrefix }
