import type { ExternalCourseSummary } from '~/utils/search'

export function courseKey(platform: string, externalId: string): string {
  return `${platform}:${externalId}`
}

export function uniqueTags(tags: string[], language: string): string[] {
  const lang = language.trim().toLowerCase()
  const seen = new Set<string>()
  const result: string[] = []
  for (const tag of tags) {
    const key = tag.trim().toLowerCase()
    if (!key || (lang && key === lang)) {
      continue
    }
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    result.push(tag.trim())
  }
  return result.slice(0, 6)
}

export function inferTagsFromText(text: string): string[] {
  const hay = ` ${text.toLowerCase()} `
  const mapping: Array<[string, string[]]> = [
    ['Python', ['python']],
    ['C++', ['c++', 'cpp']],
    ['Java', ['java']],
    ['JavaScript', ['javascript', ' js ']],
    ['Docker', ['docker']],
    ['SQL', ['sql']],
    ['Algorithms', ['algorithm', 'алгоритм']],
    ['ML', ['machine learning', 'data science', 'машинн']],
    ['Security', ['security', 'безопасн']],
  ]
  return mapping
    .filter(([, needles]) => needles.some((needle) => hay.includes(needle)))
    .map(([label]) => label)
}

export function inferDisplayTags(course: ExternalCourseSummary): string[] {
  const tags = [...(course.tags ?? [])]
  for (const hint of inferTagsFromText(`${course.title} ${course.description}`)) {
    if (!tags.includes(hint)) {
      tags.push(hint)
    }
  }
  return uniqueTags(tags, course.language ?? '')
}

export function courseCardMeta(row: {
  author: string
  tags: string[]
  description: string
  platform: string
  externalId: string
}): string {
  const bits: string[] = []
  if (row.author) {
    bits.push(row.author)
  }
  if (row.tags.length) {
    bits.push(row.tags.slice(0, 2).join(' · '))
  }
  if (bits.length) {
    return bits.join(' · ')
  }
  if (row.description) {
    return row.description.length > 96 ? `${row.description.slice(0, 93)}…` : row.description
  }
  return `${row.platform}-${row.externalId}`
}

export function cardInitial(title: string, locale = 'en'): string {
  const cleaned = title.trim()
  if (!cleaned) {
    return '?'
  }
  if (/^c#$/i.test(cleaned) || /^c#\b/i.test(cleaned)) {
    return 'C#'
  }
  if (/^c\+\+/i.test(cleaned)) {
    return 'C++'
  }
  return cleaned.charAt(0).toLocaleUpperCase(locale)
}

export function settingsLinkForPlatform(platformId: string): string {
  return `/settings?section=integration:${platformId}`
}

export function catalogTabFromQuery(value: unknown): 'library' | 'external' {
  if (value === 'discover' || value === 'external' || value === 'download') {
    return 'external'
  }
  return 'library'
}

export function catalogQueryForTab(
  current: Record<string, string>,
  tab: 'library' | 'external',
): Record<string, string> {
  if (tab === 'external') {
    return { ...current, tab: 'discover' }
  }
  return Object.fromEntries(Object.entries(current).filter(([key]) => key !== 'tab'))
}

export function chapterTitleFromOutline(
  outline: Array<{ topic_id: string; title: string }> | null | undefined,
  topicId: string,
  emptyFallback: string,
): string {
  const fromOutline = outline?.find((topic) => topic.topic_id === topicId)?.title
  if (fromOutline?.trim()) {
    return fromOutline.trim()
  }
  return topicId || emptyFallback
}

export function packPrimaryHref(
  packId: string,
  learning: { sessionId: string | null; status: string | null } | null | undefined,
): string {
  if (learning?.sessionId && learning.status === 'active') {
    return `/sessions/${learning.sessionId}`
  }
  return `/catalog/${packId}`
}

export function isActivePackLearning(
  learning: { sessionId: string | null; status: string | null } | null | undefined,
): boolean {
  return Boolean(learning?.sessionId && learning.status === 'active')
}

export function libraryCardSubtitleText(input: {
  title: string
  slug: string
  version: string | number
  chapter: string | null | undefined
  progress: number | null | undefined
  emptyLabel: string
}): string {
  const chapter = input.chapter?.trim() ?? ''
  const title = input.title.trim().toLowerCase()
  if (chapter && chapter.toLowerCase() !== title && chapter.toLowerCase() !== input.slug.toLowerCase()) {
    return chapter
  }
  if (input.progress == null) {
    return input.emptyLabel
  }
  return `v${input.version}`
}

export function platformHintText(
  message: string | null | undefined,
  fallback: string,
): string {
  return message?.trim() ? message : fallback
}

export type PackContentTagId = 'theory' | 'video' | 'quiz' | 'practice'

export function packContentTags(pack: {
  has_theory?: boolean
  has_video?: boolean
  has_quiz?: boolean
  has_practice?: boolean
}): PackContentTagId[] {
  const tags: PackContentTagId[] = []
  if (pack.has_theory) {
    tags.push('theory')
  }
  if (pack.has_video) {
    tags.push('video')
  }
  if (pack.has_quiz) {
    tags.push('quiz')
  }
  if (pack.has_practice) {
    tags.push('practice')
  }
  return tags
}
