import { describe, expect, it } from 'vitest'
import {
  canRedownloadPack,
  courseDownloadKey,
  downloadProgressPercent,
  isBrokenPack,
} from './packStatus'
import { courseKey } from './display'

describe('catalog/packStatus', () => {
  it('detects broken packs', () => {
    expect(isBrokenPack({ integrity: 'broken' })).toBe(true)
    expect(isBrokenPack({ integrity: 'ok' })).toBe(false)
    expect(isBrokenPack(null)).toBe(false)
  })

  it('allows redownload only for remote broken packs', () => {
    expect(
      canRedownloadPack({
        integrity: 'broken',
        external_id: '1',
        source: 'stepik',
      }),
    ).toBe(true)
    expect(
      canRedownloadPack({
        integrity: 'broken',
        external_id: '1',
        source: 'local',
      }),
    ).toBe(false)
  })

  it('builds download keys', () => {
    expect(
      courseDownloadKey({ external_id: '7', source: 'stepik' }, courseKey),
    ).toBe('stepik:7')
    expect(courseDownloadKey({ source: 'stepik' }, courseKey)).toBe('')
  })

  it('maps import stages to progress', () => {
    expect(downloadProgressPercent({ queued: true, importing: false })).toBe(12)
    expect(downloadProgressPercent({ queued: false, importing: true, status: 'fetching' })).toBe(58)
    expect(downloadProgressPercent({ queued: false, importing: true, status: 'building' })).toBe(92)
    expect(downloadProgressPercent({ queued: false, importing: false })).toBe(0)
  })
})
