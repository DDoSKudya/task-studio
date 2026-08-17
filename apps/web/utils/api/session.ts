type SetCookieCapableHeaders = Headers & {
  getSetCookie?: () => string[]
}

export function readSetCookieHeaders(headers: Headers): string[] {
  const capable = headers as SetCookieCapableHeaders
  if (typeof capable.getSetCookie === 'function') {
    return capable.getSetCookie().filter(Boolean)
  }
  const single = headers.get('set-cookie')
  return single ? [single] : []
}

export function shouldRotateSession(options: {
  path: string
  statusCode: number
  retried: boolean
  onClient: boolean
}): boolean {
  if (!options.onClient || options.retried || options.statusCode !== 401) {
    return false
  }
  return !options.path.startsWith('/v1/auth/')
}
