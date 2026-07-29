export function extractErrorMessage(error: unknown): string {
  if (!error || typeof error !== 'object') {
    return ''
  }
  const data = 'data' in error ? (error as { data?: { detail?: unknown } }).data : undefined
  const detail = data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim()
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') {
          return item
        }
        if (item && typeof item === 'object' && 'msg' in item) {
          const msg = (item as { msg?: unknown }).msg
          return typeof msg === 'string' ? msg : ''
        }
        return ''
      })
      .filter(Boolean)
    if (parts.length) {
      return parts.join('; ')
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return ''
}
