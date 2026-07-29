import { describe, expect, it } from 'vitest'
import {
  buildLibraryCoursePayload,
  canStartLibraryBuild,
  emptyLibraryDraft,
  isAbortError,
  libraryEnabledStages,
  looksLikeHttpUrl,
  packFilenameFromManifest,
  parseConsistencyGateDetail,
  planFillDraft,
  removeLibraryDraft,
  usableLibraryDrafts,
} from './libraryCourseCreate'

describe('libraryCourseCreate', () => {
  it('filters usable drafts and stages', () => {
    const short = emptyLibraryDraft('a')
    const long = { ...emptyLibraryDraft('b'), content: 'x'.repeat(40) }
    expect(usableLibraryDrafts([short, long])).toHaveLength(1)
    expect(libraryEnabledStages({ includeTheory: true, includeQuizzes: false, includeCode: true })).toEqual([
      'analyze',
      'theory',
      'polish',
      'code',
      'assemble',
    ])
    expect(
      canStartLibraryBuild({
        usableCount: 1,
        running: false,
        urlFetching: false,
        includeTheory: true,
        includeQuizzes: false,
        includeCode: false,
      }),
    ).toBe(true)
  })

  it('validates urls and abort errors', () => {
    expect(looksLikeHttpUrl('https://example.com/a')).toBe(true)
    expect(looksLikeHttpUrl('ftp://x')).toBe(false)
    expect(isAbortError(new DOMException('Aborted', 'AbortError'))).toBe(true)
  })

  it('plans fill/remove draft mutations', () => {
    const base = [emptyLibraryDraft('1')]
    const filled = planFillDraft(base, { titleText: 'T', content: 'body'.repeat(20) })
    expect(filled.kind).toBe('ok')
    if (filled.kind === 'ok') {
      expect(filled.drafts[0]?.content).toContain('body')
    }
    const removed = removeLibraryDraft([emptyLibraryDraft('1'), emptyLibraryDraft('2')], '1', () =>
      emptyLibraryDraft('n'),
    )
    expect(removed.drafts).toHaveLength(1)
    expect(removed.activeKey).toBe('2')
  })

  it('builds course payload', () => {
    const payload = buildLibraryCoursePayload({
      articles: [{ title: 'A', content: 'text', videos: [{ url: ' https://v ' }, { url: '' }] }],
      title: ' Course ',
      audience: '',
      locale: 'ru',
      ignoreDeviations: false,
      includeTheory: true,
      includeQuizzes: true,
      includeCode: false,
    })
    expect(payload.title).toBe('Course')
    expect(payload.articles[0]?.videos).toEqual([{ url: ' https://v ' }])
    expect(payload.include_code).toBe(false)
  })

  it('parses gate detail and pack filenames', () => {
    expect(
      parseConsistencyGateDetail({
        deviations: [{ summary: 'x', sources: ['a'] }],
        similarity: 0.4,
        related: false,
      }),
    ).toEqual({
      deviations: [{ summary: 'x', sources: ['a'] }],
      similarity: 0.4,
      related: false,
    })
    expect(packFilenameFromManifest({ id: 'demo', version: '2.0.0' })).toBe('demo-2.0.0.studio-pack')
  })
})
