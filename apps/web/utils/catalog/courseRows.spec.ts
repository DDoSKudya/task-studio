import { describe, expect, it } from 'vitest'

import type { PackSummary } from './types'
import { buildCatalogCourseRows, canDownloadExternalCourse, groupCatalogCourseRows, stepikCardAction } from './courseRows'

function pack(partial: Partial<PackSummary> & Pick<PackSummary, 'id' | 'title' | 'slug' | 'source'>): PackSummary {
  return {
    external_id: null,
    version: '1',
    version_id: 'v1',
    installed_at: '2026-01-01T00:00:00Z',
    integrity: 'ok',
    integrity_issues: [],
    ...partial,
  }
}

describe('catalog courseRows', () => {
  it('merges catalog and installed packs without duplicates', () => {
    const installed = pack({
      id: 'p1',
      title: 'A',
      slug: 'a',
      source: 'stepik',
      external_id: '1',
    })
    const rows = buildCatalogCourseRows({
      catalog: [
        {
          platform: 'stepik',
          external_id: '1',
          title: 'A',
          description: 'd',
          author: 'x',
          language: 'en',
          tags: [],
          enrolled: true,
          is_paid: false,
        },
      ],
      packs: [
        installed,
        pack({
          id: 'p2',
          title: 'B',
          slug: 'b',
          source: 'fcc',
          external_id: '9',
          version: '2',
        }),
      ],
      platformFilter: '',
      tagFilter: '',
      searched: false,
      query: '',
      findInstalledPack: (platform, externalId) =>
        platform === 'stepik' && externalId === '1' ? installed : null,
    })
    expect(rows).toHaveLength(2)
    expect(rows.find((row) => row.externalId === '1')?.packId).toBe('p1')
    expect(rows.find((row) => row.externalId === '1')?.enrolled).toBe(true)
    expect(rows.find((row) => row.externalId === '1')?.isPaid).toBe(false)
    expect(groupCatalogCourseRows(rows).map(([platform]) => platform)).toEqual(['fcc', 'stepik'])
  })

  it('blocks Stepik download when not enrolled', () => {
    expect(canDownloadExternalCourse({ platform: 'stepik', enrolled: false })).toBe(false)
    expect(canDownloadExternalCourse({ platform: 'stepik', enrolled: null })).toBe(false)
    expect(canDownloadExternalCourse({ platform: 'stepik', enrolled: true })).toBe(true)
    expect(canDownloadExternalCourse({ platform: 'exercism', enrolled: false })).toBe(true)
  })

  it('picks Stepik card action by paid and enrollment', () => {
    expect(stepikCardAction({ platform: 'stepik', enrolled: true, isPaid: true })).toBe('download')
    expect(stepikCardAction({ platform: 'stepik', enrolled: false, isPaid: true })).toBe('goto')
    expect(stepikCardAction({ platform: 'stepik', enrolled: false, isPaid: false })).toBe('enroll')
    expect(stepikCardAction({ platform: 'stepik', enrolled: false, isPaid: null })).toBe('enroll')
  })
})
