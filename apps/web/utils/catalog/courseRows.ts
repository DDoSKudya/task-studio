import type { PackSummary } from '~/composables/useCatalog'
import type { ExternalCourseSummary } from '~/utils/search'

import { courseKey, inferDisplayTags, inferTagsFromText } from './display'

export type CatalogCourseRow = {
  key: string
  platform: string
  externalId: string
  title: string
  description: string
  author: string
  language: string
  tags: string[]
  packId: string | null
  enrolled: boolean | null
  isPaid: boolean | null
}

export function canDownloadExternalCourse(row: Pick<CatalogCourseRow, 'platform' | 'enrolled'>): boolean {
  if (row.platform !== 'stepik') {
    return true
  }
  // Only enrolled courses are downloadable; unknown/null must not look like "Скачать".
  return row.enrolled === true
}

export type StepikCardAction = 'download' | 'enroll' | 'goto'

export function stepikCardAction(
  row: Pick<CatalogCourseRow, 'platform' | 'enrolled' | 'isPaid'>,
): StepikCardAction {
  if (row.platform !== 'stepik' || row.enrolled === true) {
    return 'download'
  }
  return row.isPaid === true ? 'goto' : 'enroll'
}

export function stepikCourseUrl(externalId: string): string {
  return `https://stepik.org/course/${encodeURIComponent(externalId)}`
}

export function buildCatalogCourseRows(input: {
  catalog: ExternalCourseSummary[]
  packs: PackSummary[]
  platformFilter: string
  tagFilter: string
  searched: boolean
  query: string
  findInstalledPack: (platform: string, externalId: string) => PackSummary | null
}): CatalogCourseRow[] {
  const rows = new Map<string, CatalogCourseRow>()

  for (const course of input.catalog) {
    if (input.platformFilter && course.platform !== input.platformFilter) {
      continue
    }
    const tags = inferDisplayTags(course)
    if (input.tagFilter && !tags.includes(input.tagFilter)) {
      continue
    }
    const key = courseKey(course.platform, course.external_id)
    const pack = input.findInstalledPack(course.platform, course.external_id)
    rows.set(key, {
      key,
      platform: course.platform,
      externalId: course.external_id,
      title: course.title,
      description: course.description,
      author: course.author ?? '',
      language: course.language ?? '',
      tags,
      packId: pack?.id ?? null,
      enrolled: course.enrolled ?? null,
      isPaid: course.is_paid ?? null,
    })
  }

  for (const pack of input.packs) {
    if (!pack.source || pack.source === 'local' || !pack.external_id) {
      continue
    }
    if (input.platformFilter && pack.source !== input.platformFilter) {
      continue
    }
    const key = courseKey(pack.source, pack.external_id)
    if (rows.has(key)) {
      continue
    }
    if (input.searched && input.query.trim()) {
      const needle = input.query.trim().toLowerCase()
      const hay = `${pack.title} ${pack.slug} ${pack.source}`.toLowerCase()
      if (!hay.includes(needle)) {
        continue
      }
    }
    const tags = inferTagsFromText(pack.title)
    if (input.tagFilter && !tags.includes(input.tagFilter)) {
      continue
    }
    rows.set(key, {
      key,
      platform: pack.source,
      externalId: pack.external_id,
      title: pack.title,
      description: `${pack.slug} · v${pack.version}`,
      author: '',
      language: '',
      tags,
      packId: pack.id,
      enrolled: null,
      isPaid: null,
    })
  }

  return Array.from(rows.values()).sort((a, b) => a.title.localeCompare(b.title))
}

export function groupCatalogCourseRows(
  rows: CatalogCourseRow[],
): Array<[string, CatalogCourseRow[]]> {
  const groups = new Map<string, CatalogCourseRow[]>()
  for (const row of rows) {
    const bucket = groups.get(row.platform) ?? []
    bucket.push(row)
    groups.set(row.platform, bucket)
  }
  return Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0]))
}

export function filterLibraryPacks<T extends { title: string; slug: string; source?: string | null; version: string }>(
  packs: T[],
  query: string,
): T[] {
  const needle = query.trim().toLowerCase()
  if (!needle) {
    return packs
  }
  return packs.filter((pack) => {
    const hay = `${pack.title} ${pack.slug} ${pack.source ?? ''} ${pack.version}`.toLowerCase()
    return hay.includes(needle)
  })
}
