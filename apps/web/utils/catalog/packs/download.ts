export type DownloadQueueItem = {
  key: string
  platform: string
  externalId: string
  force: boolean
  enrollFirst?: boolean
}

export function canEnqueueDownload(input: {
  force: boolean
  healthy: boolean
  busy: boolean
}): boolean {
  if (!input.force && (input.healthy || input.busy)) {
    return false
  }
  if (input.force && input.busy) {
    return false
  }
  return true
}

export function shouldSkipQueuedDownload(input: {
  force: boolean
  healthy: boolean
  importing: boolean
}): boolean {
  if (!input.force && (input.healthy || input.importing)) {
    return true
  }
  return input.force && input.importing
}

export function withoutRecordKey<T>(
  record: Record<string, T>,
  key: string,
): Record<string, T> {
  return Object.fromEntries(Object.entries(record).filter(([entryKey]) => entryKey !== key))
}

export function catalogOpenSourceAction(
  status: string,
): 'settings' | 'select' {
  if (status === 'needs_auth' || status === 'error' || status === 'upload_only') {
    return 'settings'
  }
  return 'select'
}

export function importFailureToastMessage(
  error: unknown,
  extractMessage: (error: unknown) => string,
  t: (key: string) => string,
): string {
  if (error instanceof Error && error.message === 'timeout') {
    return t('search.errors.importTimeout')
  }
  const message = extractMessage(error)
  if (message.includes('import already in progress')) {
    return t('search.errors.importInProgress')
  }
  return message || t('search.errors.importFailed')
}
