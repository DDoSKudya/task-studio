import { describe, expect, it } from 'vitest'
import {
  canEnqueueDownload,
  catalogOpenSourceAction,
  importFailureToastMessage,
  shouldSkipQueuedDownload,
  withoutRecordKey,
} from './download'

describe('catalog/download', () => {
  it('gates enqueue and queue skip', () => {
    expect(canEnqueueDownload({ force: false, healthy: true, busy: false })).toBe(false)
    expect(canEnqueueDownload({ force: true, healthy: true, busy: false })).toBe(true)
    expect(shouldSkipQueuedDownload({ force: false, healthy: true, importing: false })).toBe(true)
    expect(shouldSkipQueuedDownload({ force: true, healthy: false, importing: true })).toBe(true)
    expect(shouldSkipQueuedDownload({ force: true, healthy: false, importing: false })).toBe(false)
  })

  it('routes open-source actions', () => {
    expect(catalogOpenSourceAction('needs_auth')).toBe('settings')
    expect(catalogOpenSourceAction('ready')).toBe('select')
  })

  it('maps import failures and strips keys', () => {
    expect(
      importFailureToastMessage(new Error('timeout'), () => '', (key) => key),
    ).toBe('search.errors.importTimeout')
    expect(withoutRecordKey({ a: 1, b: 2 }, 'a')).toEqual({ b: 2 })
  })
})
