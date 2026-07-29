import { describe, expect, it } from 'vitest'

import type { PackSummary } from './types'
import { buildCatalogCourseRows, groupCatalogCourseRows } from './courseRows'

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
    expect(groupCatalogCourseRows(rows).map(([platform]) => platform)).toEqual(['fcc', 'stepik'])
  })
})
