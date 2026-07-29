export type LibraryDraftArticle = {
  key: string
  title: string
  content: string
  sourceUrl: string
  videos: Array<{ url: string; title?: string | null }>
}

export type LibraryBuildStage =
  | 'consistency'
  | 'analyze'
  | 'theory'
  | 'polish'
  | 'quizzes'
  | 'code'
  | 'assemble'

const MAX_ARTICLES = 6
const MIN_CONTENT_LEN = 40

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
  return drafts.filter((item) => item.content.trim().length >= MIN_CONTENT_LEN)
}

export function canStartLibraryBuild(input: {
  usableCount: number
  running: boolean
  urlFetching: boolean
  includeTheory: boolean
  includeQuizzes: boolean
  includeCode: boolean
}): boolean {
  return (
    input.usableCount >= 1
    && !input.running
    && !input.urlFetching
    && (input.includeTheory || input.includeQuizzes || input.includeCode)
  )
}

export function libraryEnabledStages(input: {
  includeTheory: boolean
  includeQuizzes: boolean
  includeCode: boolean
}): LibraryBuildStage[] {
  const stages: LibraryBuildStage[] = ['analyze']
  if (input.includeTheory) {
    stages.push('theory', 'polish')
  }
  if (input.includeQuizzes) {
    stages.push('quizzes')
  }
  if (input.includeCode) {
    stages.push('code')
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
  makeEmpty: () => LibraryDraftArticle,
): { drafts: LibraryDraftArticle[]; activeKey: string } {
  if (drafts.length <= 1) {
    const only = makeEmpty()
    return { drafts: [only], activeKey: only.key }
  }
  const next = drafts.filter((item) => item.key !== key)
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
  if (drafts.length >= MAX_ARTICLES && drafts.every((item) => item.content.trim())) {
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
  if (drafts.length < MAX_ARTICLES) {
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

export function buildLibraryCoursePayload(input: {
  articles: Array<{
    title: string
    content: string
    videos?: Array<{ url: string; title?: string | null }>
  }>
  title: string
  audience: string
  locale: string
  ignoreDeviations: boolean
  includeTheory: boolean
  includeQuizzes: boolean
  includeCode: boolean
}) {
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
    runtime: 'python',
    runtime_version: '3.12',
    quiz_count: 6,
    code_count: 3,
    ignore_deviations: input.ignoreDeviations,
    include_theory: input.includeTheory,
    include_quizzes: input.includeQuizzes,
    include_code: input.includeCode,
  }
}

export function parseConsistencyGateDetail(detail: Record<string, unknown> | null | undefined): {
  deviations: Array<{ summary: string; sources: string[] }>
  similarity: number | null
  related: boolean
} {
  const body = detail ?? {}
  return {
    deviations: Array.isArray(body.deviations)
      ? (body.deviations as Array<{ summary: string; sources: string[] }>)
      : [],
    similarity: typeof body.similarity === 'number' ? body.similarity : null,
    related: body.related !== false,
  }
}

export function packFilenameFromManifest(manifest: Record<string, unknown>): string {
  const slug = typeof manifest.id === 'string' ? manifest.id : 'pack'
  const version = typeof manifest.version === 'string' ? manifest.version : '1.0.0'
  return `${slug}-${version}.studio-pack`
}
