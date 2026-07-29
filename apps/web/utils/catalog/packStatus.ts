export type PackIntegrityLike = {
  integrity?: string | null
  external_id?: string | null
  source?: string | null
}

export function isBrokenPack(pack: PackIntegrityLike | null | undefined): boolean {
  return pack?.integrity === 'broken'
}

export function canRedownloadPack(pack: PackIntegrityLike): boolean {
  return (
    isBrokenPack(pack)
    && Boolean(pack.external_id)
    && Boolean(pack.source)
    && pack.source !== 'local'
  )
}

export function courseDownloadKey(
  pack: PackIntegrityLike,
  keyFn: (platform: string, externalId: string) => string,
): string {
  if (!pack.external_id) {
    return ''
  }
  return keyFn(pack.source ?? '', pack.external_id)
}


export function downloadProgressPercent(input: {
  queued: boolean
  importing: boolean
  status?: string
}): number {
  if (input.queued && !input.importing) {
    return 12
  }
  const status = input.status
  if (status === 'starting') {
    return 22
  }
  if (status === 'pending') {
    return 34
  }
  if (status === 'fetching') {
    return 58
  }
  if (status === 'normalizing') {
    return 78
  }
  if (status === 'building') {
    return 92
  }
  if (status === 'done') {
    return 100
  }
  return input.importing || input.queued ? 16 : 0
}
