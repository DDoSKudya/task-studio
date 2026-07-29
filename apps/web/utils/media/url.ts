
export function resolveMediaSrc(apiBase: string, value: string | null | undefined): string {
  if (!value || !value.trim()) {
    return ''
  }
  const trimmed = value.trim()
  const base = apiBase.replace(/\/$/, '')
  if (trimmed.startsWith('/')) {
    return `${base}${trimmed}`
  }
  return trimmed
}

export function resolveAssetIdSrc(apiBase: string, assetId: string | null | undefined): string {
  if (!assetId || !assetId.trim()) {
    return ''
  }
  const id = assetId.trim().replace(/^\/+/, '')
  return `${apiBase.replace(/\/$/, '')}/v1/media/${id}`
}
