import type { ImportJobResponse } from '~/composables/useSearch'
import { extractErrorMessage } from '~/utils/api'
import {
  canEnqueueDownload,
  courseKey,
  downloadProgressPercent as downloadStagePercent,
  importFailureToastMessage,
  shouldSkipQueuedDownload,
  withoutRecordKey,
  type DownloadQueueItem,
} from '~/utils/catalog'

type ImportUiState = {
  status: ImportJobResponse['status'] | 'starting' | 'enrolling'
}

const POLL_MS = 900
const POLL_TIMEOUT_MS = 5 * 60_000

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function useCatalogDownloads(options: {
  isHealthyInstall: (platform: string, externalId: string) => boolean
  findInstalledTitle: (platform: string, externalId: string) => string | null
  refreshPacks: () => Promise<void>
  onEnrolled?: (platform: string, externalId: string) => void | Promise<void>
}) {
  const { t } = useI18n()
  const { importFromSearch, enrollCourse, getImportJob } = useSearch()
  const toasts = useToasts()

  const importStates = ref<Record<string, ImportUiState>>({})
  const downloadQueue = ref<DownloadQueueItem[]>([])
  let drainRunning = false

  function isImporting(key: string) {
    return Boolean(importStates.value[key])
  }

  function isQueued(key: string) {
    return downloadQueue.value.some((item) => item.key === key)
  }

  function isDownloadBusy(key: string) {
    return isImporting(key) || isQueued(key)
  }

  function downloadProgressPercent(key: string) {
    return downloadStagePercent({
      queued: isQueued(key),
      importing: isImporting(key),
      status: importStates.value[key]?.status,
    })
  }

  async function waitForImportJob(jobId: string, key: string) {
    const deadline = Date.now() + POLL_TIMEOUT_MS
    while (Date.now() < deadline) {
      const job = await getImportJob(jobId)
      importStates.value = { ...importStates.value, [key]: { status: job.status } }
      if (job.status === 'done') {
        return job
      }
      if (job.status === 'failed') {
        throw new Error(job.error || 'failed')
      }
      await sleep(POLL_MS)
    }
    throw new Error('timeout')
  }

  async function runDownload(
    platform: string,
    externalId: string,
    force = false,
    enrollFirst = false,
  ) {
    const key = courseKey(platform, externalId)
    if (!force && options.isHealthyInstall(platform, externalId)) {
      return
    }

    importStates.value = {
      ...importStates.value,
      [key]: { status: enrollFirst ? 'enrolling' : 'starting' },
    }

    try {
      if (enrollFirst) {
        await enrollCourse(platform, externalId)
        await options.onEnrolled?.(platform, externalId)
      }
      importStates.value = { ...importStates.value, [key]: { status: 'starting' } }
      const accepted = await importFromSearch(platform, externalId, { force })
      await waitForImportJob(accepted.id, key)
      await options.refreshPacks()
      toasts.success(
        t('search.downloadDone', {
          title: options.findInstalledTitle(platform, externalId) ?? externalId,
        }),
      )
    } catch (error) {
      toasts.error(importFailureToastMessage(error, extractErrorMessage, t))
    } finally {
      importStates.value = withoutRecordKey(importStates.value, key)
    }
  }

  async function drainDownloadQueue() {
    if (drainRunning) {
      return
    }
    drainRunning = true
    try {
      while (downloadQueue.value.length) {
        const next = downloadQueue.value[0]
        if (!next) {
          break
        }
        downloadQueue.value = downloadQueue.value.slice(1)
        if (
          shouldSkipQueuedDownload({
            force: next.force,
            healthy: options.isHealthyInstall(next.platform, next.externalId),
            importing: isImporting(next.key),
          })
        ) {
          continue
        }
        await runDownload(next.platform, next.externalId, next.force, Boolean(next.enrollFirst))
      }
    } finally {
      drainRunning = false
      if (downloadQueue.value.length) {
        void drainDownloadQueue()
      }
    }
  }

  function enqueueDownload(
    platform: string,
    externalId: string,
    force = false,
    optionsExtra: { enrollFirst?: boolean } = {},
  ) {
    const key = courseKey(platform, externalId)
    if (
      !canEnqueueDownload({
        force,
        healthy: options.isHealthyInstall(platform, externalId),
        busy: isDownloadBusy(key),
      })
    ) {
      return
    }
    downloadQueue.value = [
      ...downloadQueue.value,
      {
        key,
        platform,
        externalId,
        force,
        enrollFirst: Boolean(optionsExtra.enrollFirst),
      },
    ]
    void drainDownloadQueue()
  }

  return {
    importStates,
    downloadQueue,
    isImporting,
    isQueued,
    isDownloadBusy,
    downloadProgressPercent,
    enqueueDownload,
  }
}
