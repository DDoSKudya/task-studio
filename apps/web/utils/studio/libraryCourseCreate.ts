import type { CourseFromArticleBody } from './courseStream'

export type LibraryDraftArticle = {
  key: string
  title: string
  content: string
  sourceUrl: string
  videos: Array<{ url: string; title?: string | null }>
}

export type LibraryBuildStage =
  | 'analyze'
  | 'code_suitability'
  | 'theory'
  | 'polish'
  | 'quizzes'
  | 'code'
  | 'topic_bundle'
  | 'assemble'

export type LibraryProgressStage = Exclude<
  LibraryBuildStage,
  'code_suitability' | 'topic_bundle'
>

export const LIBRARY_MAX_ARTICLES = 50
export const LIBRARY_MIN_CONTENT_LEN = 40

export type CourseDepth = 'light' | 'standard' | 'deep'
export type CourseLayout = 'phased' | 'by_topic'
export type CodeSuitabilityAction = 'keep_code' | 'open_tasks' | 'no_practice'
export type PracticeLevel = 'easy' | 'medium' | 'hard'

export function practiceLadderLevels(count: number): PracticeLevel[] {
  const n = Math.max(0, Math.min(12, Math.floor(Number(count) || 0)))
  const order: PracticeLevel[] = ['easy', 'medium', 'hard']
  return Array.from({ length: n }, (_, index) => order[index % 3]!)
}

export type PracticeLevelLabels = {
  easy: { one: string; many: string }
  medium: { one: string; many: string }
  hard: { one: string; many: string }
}

export function practiceLadderSummary(
  count: number,
  labels: PracticeLevelLabels,
): string {
  const levels = practiceLadderLevels(count)
  if (!levels.length) {
    return ''
  }
  const tallies = { easy: 0, medium: 0, hard: 0 }
  for (const level of levels) {
    tallies[level] += 1
  }
  const parts: string[] = []
  if (tallies.easy) {
    parts.push(
      tallies.easy === 1 ? labels.easy.one : `${tallies.easy}× ${labels.easy.many}`,
    )
  }
  if (tallies.medium) {
    parts.push(
      tallies.medium === 1
        ? labels.medium.one
        : `${tallies.medium}× ${labels.medium.many}`,
    )
  }
  if (tallies.hard) {
    parts.push(
      tallies.hard === 1 ? labels.hard.one : `${tallies.hard}× ${labels.hard.many}`,
    )
  }
  return parts.join(' · ')
}

export function newDraftKey(now = Date.now(), random = Math.random): string {
  return `${now}-${random().toString(36).slice(2, 8)}`
}

export function emptyLibraryDraft(key = newDraftKey()): LibraryDraftArticle {
  return {
    key,
    title: '',
    content: '',
    sourceUrl: '',
    videos: [],
  }
}

export function usableLibraryDrafts(drafts: LibraryDraftArticle[]): LibraryDraftArticle[] {
  return drafts.filter((item) => item.content.trim().length >= LIBRARY_MIN_CONTENT_LEN)
}

export function canStartLibraryBuild(input: {
  usableCount: number
  running: boolean
  urlFetching: boolean
  includeQuizzes?: boolean
  includeCode?: boolean
}): boolean {

  return input.usableCount >= 1 && !input.running && !input.urlFetching
}

export type LibraryContentMix = {
  includeQuizzes: boolean
  includeCode: boolean
}

export function libraryContentMixKey(
  input: LibraryContentMix,
): 'theoryOnly' | 'theoryQuizzes' | 'theoryCode' | 'theoryQuizzesCode' {
  if (input.includeQuizzes && input.includeCode) {
    return 'theoryQuizzesCode'
  }
  if (input.includeQuizzes) {
    return 'theoryQuizzes'
  }
  if (input.includeCode) {
    return 'theoryCode'
  }
  return 'theoryOnly'
}

export function libraryEnabledStages(input: {
  includeQuizzes: boolean
  includeCode: boolean
  layout?: CourseLayout
}): LibraryProgressStage[] {
  const stages: LibraryProgressStage[] = ['analyze', 'theory', 'polish']
  const byTopic = (input.layout ?? 'by_topic') === 'by_topic'

  if (!byTopic) {
    if (input.includeQuizzes) {
      stages.push('quizzes')
    }
    if (input.includeCode) {
      stages.push('code')
    }
  }
  stages.push('assemble')
  return stages
}

export function looksLikeHttpUrl(value: string): boolean {
  try {
    const parsed = new URL(value.trim())
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

const URL_IN_TEXT = /https?:\/\/[^\s<>"'`|,;]+/gi
const TRAILING_URL_PUNCT = /[.,;:!?)\]]+$/g
const URL_LIST_SPLIT = /[\n\r,;|]+/g

export function extractHttpUrls(text: string, limit = 20): string[] {
  const found: string[] = []
  const seen = new Set<string>()
  const cap = Math.max(1, Math.min(limit, 20))

  const add = (raw: string) => {
    const cleaned = raw.trim().replace(TRAILING_URL_PUNCT, '')
    if (!looksLikeHttpUrl(cleaned) || seen.has(cleaned)) {
      return
    }
    seen.add(cleaned)
    found.push(cleaned)
  }

  for (const line of text.replace(URL_LIST_SPLIT, '\n').split('\n')) {
    const piece = line.trim()
    if (piece.startsWith('http://') || piece.startsWith('https://')) {
      if (!/\s/.test(piece)) {
        add(piece)
      }
    }
  }
  for (const match of text.matchAll(URL_IN_TEXT)) {
    add(match[0] ?? '')
    if (found.length >= cap) {
      break
    }
  }
  return found.slice(0, cap)
}

export function isAbortError(error: unknown, signal?: AbortSignal | null): boolean {
  if (signal?.aborted) {
    return true
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return true
  }
  if (typeof error === 'object' && error !== null) {
    const err = error as { name?: string; message?: string }
    if (err.name === 'AbortError') {
      return true
    }
    if (typeof err.message === 'string' && /abort/i.test(err.message)) {
      return true
    }
  }
  return false
}

export function removeLibraryDraft(
  drafts: LibraryDraftArticle[],
  key: string,
  _makeEmpty?: () => LibraryDraftArticle,
): { drafts: LibraryDraftArticle[]; activeKey: string } {
  const next = drafts.filter((item) => item.key !== key)
  if (!next.length) {
    return { drafts: [], activeKey: '' }
  }
  return { drafts: next, activeKey: next[0].key }
}

export function planFillDraft(
  drafts: LibraryDraftArticle[],
  input: {
    titleText: string
    content: string
    sourceUrl?: string
    videos?: Array<{ url: string; title?: string | null }>
  },
  makeKey: () => string = newDraftKey,
):
  | { kind: 'max' }
  | {
      kind: 'ok'
      drafts: LibraryDraftArticle[]
      activeKey: string
    } {
  const videos = input.videos ?? []
  const sourceUrl = input.sourceUrl ?? ''
  if (drafts.length >= LIBRARY_MAX_ARTICLES && drafts.every((item) => item.content.trim())) {
    return { kind: 'max' }
  }
  const empty = drafts.find((item) => !item.content.trim())
  if (empty) {
    const next = drafts.map((item) =>
      item.key === empty.key
        ? {
            ...item,
            title: item.title || input.titleText,
            content: input.content,
            sourceUrl: sourceUrl || item.sourceUrl,
            videos: videos.length ? videos : item.videos,
          }
        : item,
    )
    return { kind: 'ok', drafts: next, activeKey: empty.key }
  }
  if (drafts.length < LIBRARY_MAX_ARTICLES) {
    const key = makeKey()
    return {
      kind: 'ok',
      drafts: [
        ...drafts,
        {
          key,
          title: input.titleText,
          content: input.content,
          sourceUrl,
          videos,
        },
      ],
      activeKey: key,
    }
  }
  return { kind: 'max' }
}

type LibraryCoursePayload = CourseFromArticleBody & {
  articles: NonNullable<CourseFromArticleBody['articles']>
}

export function buildLibraryCoursePayload(input: {
  articles: Array<{
    title: string
    content: string
    videos?: Array<{ url: string; title?: string | null }>
  }>
  title: string
  audience: string
  locale: string
  courseDepth: CourseDepth
  layout: CourseLayout
  quizCount: number
  practiceCount: number
  includeQuizzes: boolean
  includeCode: boolean
  codeSuitabilityAction?: CodeSuitabilityAction | null
  buildId?: string | null
}): LibraryCoursePayload {
  return {
    articles: input.articles.map((item) => ({
      title: item.title,
      content: item.content,
      videos: item.videos?.length
        ? item.videos.filter((video) => typeof video.url === 'string' && video.url.trim())
        : undefined,
    })),
    title: input.title.trim() || null,
    audience: input.audience.trim() || null,
    locale: input.locale || 'ru',
    course_depth: input.courseDepth,
    layout: input.layout,
    split_long_theory: true,
    include_theory: true,
    theory_count: null,
    quiz_count: input.quizCount,
    practice_count: input.practiceCount,
    code_count: input.practiceCount,
    include_quizzes: input.includeQuizzes,
    include_code: input.includeCode,
    code_suitability_policy: 'ask',
    code_suitability_action: input.codeSuitabilityAction ?? null,
    build_id: input.buildId ?? null,
  }
}

export function parseCodeSuitabilityGateDetail(detail: Record<string, unknown> | null | undefined): {
  score: number | null
  profile: string | null
  options: CodeSuitabilityAction[]
} {
  const body = detail ?? {}
  const rawOptions = Array.isArray(body.options) ? body.options : []
  const options = rawOptions.filter(
    (item): item is CodeSuitabilityAction =>
      item === 'keep_code' || item === 'open_tasks' || item === 'no_practice',
  )
  return {
    score: typeof body.score === 'number' ? body.score : null,
    profile: typeof body.profile === 'string' ? body.profile : null,
    options: options.length ? options : ['keep_code', 'open_tasks', 'no_practice'],
  }
}

export function packFilenameFromManifest(manifest: Record<string, unknown>): string {
  const slug = typeof manifest.id === 'string' ? manifest.id : 'pack'
  const version = typeof manifest.version === 'string' ? manifest.version : '1.0.0'
  return `${slug}-${version}.studio-pack`
}

export type SavedCourseBuildRequest = {
  title?: string | null
  audience?: string | null
  locale?: string | null
  articles?: Array<{
    title?: string | null
    content?: string | null
    videos?: Array<{ url: string; title?: string | null }> | null
  }> | null
  article?: string | null
  include_quizzes?: boolean
  include_code?: boolean
  course_depth?: CourseDepth | string | null
  layout?: CourseLayout | string | null
  quiz_count?: number | null
  practice_count?: number | null
  code_suitability_action?: CodeSuitabilityAction | null
  ignore_deviations?: boolean
}

export type HydratedLibraryForm = {
  drafts: LibraryDraftArticle[]
  activeKey: string
  title: string
  audience: string
  locale: string
  includeQuizzes: boolean
  includeCode: boolean
  courseDepth: CourseDepth
  layout: CourseLayout
  quizCount: number | null
  practiceCount: number | null
  pendingCodeAction: CodeSuitabilityAction | null
}

function _asDepth(value: unknown): CourseDepth {
  return value === 'light' || value === 'deep' ? value : 'standard'
}

function _asLayout(value: unknown): CourseLayout {
  return value === 'phased' ? 'phased' : 'by_topic'
}

export function hydrateLibraryFormFromRequest(
  request: SavedCourseBuildRequest | Record<string, unknown>,
  makeKey: () => string = newDraftKey,
): HydratedLibraryForm {
  const body = request as SavedCourseBuildRequest
  const drafts: LibraryDraftArticle[] = []
  if (Array.isArray(body.articles) && body.articles.length) {
    for (const item of body.articles) {
      const content = typeof item?.content === 'string' ? item.content : ''
      if (!content.trim()) {
        continue
      }
      drafts.push({
        key: makeKey(),
        title: typeof item?.title === 'string' ? item.title : '',
        content,
        sourceUrl: '',
        videos: Array.isArray(item?.videos)
          ? item.videos.filter((v): v is { url: string; title?: string | null } =>
              Boolean(v && typeof v.url === 'string'),
            )
          : [],
      })
    }
  } else if (typeof body.article === 'string' && body.article.trim()) {
    drafts.push({
      ...emptyLibraryDraft(makeKey()),
      content: body.article,
    })
  }
  if (!drafts.length) {
    drafts.push(emptyLibraryDraft(makeKey()))
  }
  const codeAction = body.code_suitability_action
  return {
    drafts,
    activeKey: drafts[0].key,
    title: typeof body.title === 'string' ? body.title : '',
    audience: typeof body.audience === 'string' ? body.audience : '',
    locale: typeof body.locale === 'string' && body.locale.trim() ? body.locale : 'ru',
    includeQuizzes: body.include_quizzes !== false,
    includeCode: body.include_code !== false,
    courseDepth: _asDepth(body.course_depth),
    layout: _asLayout(body.layout),
    quizCount: typeof body.quiz_count === 'number' ? body.quiz_count : null,
    practiceCount: typeof body.practice_count === 'number' ? body.practice_count : null,
    pendingCodeAction:
      codeAction === 'keep_code' || codeAction === 'open_tasks' || codeAction === 'no_practice'
        ? codeAction
        : null,
  }
}

export function buildResumeCoursePayload(input: {
  buildId: string
  codeSuitabilityAction?: CodeSuitabilityAction | null
}): Record<string, unknown> {
  return {
    build_id: input.buildId,
    code_suitability_action: input.codeSuitabilityAction ?? null,
  }
}
