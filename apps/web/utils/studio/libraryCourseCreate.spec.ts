import { describe, expect, it } from 'vitest'
import {
  buildLibraryCoursePayload,
  buildResumeCoursePayload,
  canStartLibraryBuild,
  emptyLibraryDraft,
  hydrateLibraryFormFromRequest,
  isAbortError,
  libraryEnabledStages,
  libraryContentMixKey,
  looksLikeHttpUrl,
  extractHttpUrls,
  packFilenameFromManifest,
  planFillDraft,
  practiceLadderLevels,
  practiceLadderSummary,
  removeLibraryDraft,
  usableLibraryDrafts,
} from './libraryCourseCreate'

describe('libraryCourseCreate', () => {
  it('filters usable drafts and stages', () => {
    const short = emptyLibraryDraft('a')
    const long = { ...emptyLibraryDraft('b'), content: 'x'.repeat(40) }
    expect(usableLibraryDrafts([short, long])).toHaveLength(1)
    expect(
      libraryEnabledStages({
        includeQuizzes: true,
        includeCode: true,
      }),
    ).toEqual(['analyze', 'theory', 'polish', 'assemble'])
    expect(libraryEnabledStages({ includeQuizzes: false, includeCode: true })).toEqual([
      'analyze',
      'theory',
      'polish',
      'assemble',
    ])
    expect(
      libraryEnabledStages({
        includeQuizzes: false,
        includeCode: false,
        layout: 'by_topic',
      }),
    ).toEqual(['analyze', 'theory', 'polish', 'assemble'])
    expect(
      libraryEnabledStages({
        includeQuizzes: true,
        includeCode: true,
        layout: 'phased',
      }),
    ).toEqual(['analyze', 'theory', 'polish', 'quizzes', 'code', 'assemble'])
    expect(
      libraryEnabledStages({
        includeQuizzes: true,
        includeCode: false,
        layout: 'phased',
      }),
    ).toEqual(['analyze', 'theory', 'polish', 'quizzes', 'assemble'])
    expect(
      canStartLibraryBuild({
        usableCount: 1,
        running: false,
        urlFetching: false,
        includeQuizzes: true,
        includeCode: false,
      }),
    ).toBe(true)
    expect(
      canStartLibraryBuild({
        usableCount: 1,
        running: false,
        urlFetching: false,
        includeQuizzes: false,
        includeCode: false,
      }),
    ).toBe(true)
    expect(libraryContentMixKey({ includeQuizzes: false, includeCode: false })).toBe('theoryOnly')
    expect(libraryContentMixKey({ includeQuizzes: true, includeCode: false })).toBe(
      'theoryQuizzes',
    )
    expect(libraryContentMixKey({ includeQuizzes: false, includeCode: true })).toBe('theoryCode')
    expect(libraryContentMixKey({ includeQuizzes: true, includeCode: true })).toBe(
      'theoryQuizzesCode',
    )
  })

  it('validates urls and abort errors', () => {
    expect(looksLikeHttpUrl('https://example.com/a')).toBe(true)
    expect(looksLikeHttpUrl('ftp://x')).toBe(false)
    expect(isAbortError(new DOMException('Aborted', 'AbortError'))).toBe(true)
  })

  it('extracts several urls from a pasted blob', () => {
    const urls = extractHttpUrls(`
      https://example.com/a
      see also https://example.com/b,
      https://example.com/a
      ftp://ignore.me/x
    `)
    expect(urls).toEqual(['https://example.com/a', 'https://example.com/b'])
  })

  it('accepts comma semicolon and pipe separators', () => {
    expect(
      extractHttpUrls(
        'https://example.com/a, https://example.com/b;https://example.com/c|https://example.com/d',
      ),
    ).toEqual([
      'https://example.com/a',
      'https://example.com/b',
      'https://example.com/c',
      'https://example.com/d',
    ])
  })

  it('plans fill/remove draft mutations', () => {
    const base = [emptyLibraryDraft('1')]
    const filled = planFillDraft(base, { titleText: 'T', content: 'body'.repeat(20) })
    expect(filled.kind).toBe('ok')
    if (filled.kind === 'ok') {
      expect(filled.drafts[0]?.content).toContain('body')
    }
    const removed = removeLibraryDraft([emptyLibraryDraft('1'), emptyLibraryDraft('2')], '1')
    expect(removed.drafts).toHaveLength(1)
    expect(removed.activeKey).toBe('2')
    const cleared = removeLibraryDraft([emptyLibraryDraft('1')], '1')
    expect(cleared.drafts).toHaveLength(0)
    expect(cleared.activeKey).toBe('')
  })

  it('builds course payload with theory always on', () => {
    const payload = buildLibraryCoursePayload({
      articles: [{ title: 'A', content: 'text', videos: [{ url: ' https://v ' }, { url: '' }] }],
      title: ' Course ',
      audience: '',
      locale: 'ru',
      courseDepth: 'standard',
      layout: 'phased',
      quizCount: 12,
      practiceCount: 2,
      includeQuizzes: true,
      includeCode: false,
    })
    expect(payload.title).toBe('Course')
    expect(payload.include_theory).toBe(true)
    expect(payload.theory_count).toBeNull()
    expect(payload.layout).toBe('phased')
    expect(payload.split_long_theory).toBe(true)
    expect(payload.quiz_count).toBe(12)
    expect(payload.articles[0]?.videos).toEqual([{ url: ' https://v ' }])
    expect(payload.include_code).toBe(false)
    expect(payload.locale).toBe('ru')
  })

  it('puts the selected course language on the payload', () => {
    const payload = buildLibraryCoursePayload({
      articles: [{ title: 'A', content: 'x'.repeat(50) }],
      title: 'Pathlib',
      audience: '',
      locale: 'en',
      courseDepth: 'standard',
      layout: 'by_topic',
      quizCount: 4,
      practiceCount: 2,
      includeQuizzes: true,
      includeCode: true,
    })
    expect(payload.locale).toBe('en')
  })

  it('hydrates drafts and options from saved build request', () => {
    let n = 0
    const hydrated = hydrateLibraryFormFromRequest(
      {
        title: 'Docker',
        audience: 'devs',
        locale: 'ru',
        include_quizzes: false,
        include_code: true,
        course_depth: 'deep',
        layout: 'phased',
        articles: [
          { title: 'A', content: 'x'.repeat(50), videos: [{ url: 'https://youtu.be/a' }] },
          { title: 'B', content: 'y'.repeat(50) },
        ],
      },
      () => `k-${n++}`,
    )
    expect(hydrated.drafts).toHaveLength(2)
    expect(hydrated.title).toBe('Docker')
    expect(hydrated.includeQuizzes).toBe(false)
    expect(hydrated.courseDepth).toBe('deep')
    expect(hydrated.layout).toBe('phased')
    expect(usableLibraryDrafts(hydrated.drafts)).toHaveLength(2)
  })

  it('builds resume payload with build_id only', () => {
    expect(
      buildResumeCoursePayload({
        buildId: '11111111-1111-1111-1111-111111111111',
        codeSuitabilityAction: 'keep_code',
      }),
    ).toEqual({
      build_id: '11111111-1111-1111-1111-111111111111',
      code_suitability_action: 'keep_code',
    })
  })

  it('builds practice ladder by round-robin difficulty', () => {
    expect(practiceLadderLevels(1)).toEqual(['easy'])
    expect(practiceLadderLevels(2)).toEqual(['easy', 'medium'])
    expect(practiceLadderLevels(3)).toEqual(['easy', 'medium', 'hard'])
    expect(practiceLadderLevels(4)).toEqual(['easy', 'medium', 'hard', 'easy'])
    expect(practiceLadderLevels(6)).toEqual([
      'easy',
      'medium',
      'hard',
      'easy',
      'medium',
      'hard',
    ])
    expect(practiceLadderLevels(8)).toEqual([
      'easy',
      'medium',
      'hard',
      'easy',
      'medium',
      'hard',
      'easy',
      'medium',
    ])
    const twelve = practiceLadderLevels(12)
    expect(twelve.filter((level) => level === 'easy')).toHaveLength(4)
    expect(twelve.filter((level) => level === 'medium')).toHaveLength(4)
    expect(twelve.filter((level) => level === 'hard')).toHaveLength(4)
  })

  it('summarizes practice ladder tallies', () => {
    expect(
      practiceLadderSummary(8, {
        easy: { one: 'лёгкое', many: 'лёгких' },
        medium: { one: 'нормальное', many: 'нормальных' },
        hard: { one: 'сложное', many: 'сложных' },
      }),
    ).toBe('3× лёгких · 3× нормальных · 2× сложных')
    expect(
      practiceLadderSummary(3, {
        easy: { one: 'лёгкое', many: 'лёгких' },
        medium: { one: 'нормальное', many: 'нормальных' },
        hard: { one: 'сложное', many: 'сложных' },
      }),
    ).toBe('лёгкое · нормальное · сложное')
  })

  it('builds pack filenames', () => {
    expect(packFilenameFromManifest({ id: 'demo', version: '2.0.0' })).toBe('demo-2.0.0.studio-pack')
  })
})
