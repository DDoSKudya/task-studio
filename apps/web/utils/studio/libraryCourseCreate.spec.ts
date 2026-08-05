import { describe, expect, it } from 'vitest'
import {
  buildLibraryCoursePayload,
  buildResumeCoursePayload,
  canStartLibraryBuild,
  emptyLibraryDraft,
  hydrateLibraryFormFromRequest,
  isAbortError,
  libraryEnabledStages,
  looksLikeHttpUrl,
  extractHttpUrls,
  packFilenameFromManifest,
  parseConsistencyGateDetail,
  planFillDraft,
  practiceLadderLevels,
  practiceLadderSummary,
  removeLibraryDraft,
  suggestCourseScale,
  suggestCourseScaleFromDrafts,
  totalLibraryContentChars,
  usableLibraryDrafts,
} from './libraryCourseCreate'

describe('libraryCourseCreate', () => {
    it('filters usable drafts and stages', () => {
    const short = emptyLibraryDraft('a')
    const long = { ...emptyLibraryDraft('b'), content: 'x'.repeat(40) }
    expect(usableLibraryDrafts([short, long])).toHaveLength(1)
    expect(libraryEnabledStages({ includeTheory: true, includeQuizzes: false, includeCode: true })).toEqual([
      'analyze',
      'code_suitability',
      'topic_bundle',
      'theory',
      'polish',
      'code',
      'assemble',
    ])
    expect(
      libraryEnabledStages({
        includeTheory: true,
        includeQuizzes: true,
        includeCode: false,
        layout: 'phased',
      }),
    ).toEqual(['analyze', 'code_suitability', 'theory', 'polish', 'quizzes', 'assemble'])
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

  it('builds course payload', () => {
    const payload = buildLibraryCoursePayload({
      articles: [{ title: 'A', content: 'text', videos: [{ url: ' https://v ' }, { url: '' }] }],
      title: ' Course ',
      audience: '',
      locale: 'ru',
      courseDepth: 'standard',
      layout: 'phased',
      splitLongTheory: true,
      theoryCount: 20,
      quizCount: 12,
      practiceCount: 2,
      ignoreDeviations: false,
      includeTheory: true,
      includeQuizzes: true,
      includeCode: false,
    })
    expect(payload.title).toBe('Course')
    expect(payload.theory_count).toBe(20)
    expect(payload.layout).toBe('phased')
    expect(payload.split_long_theory).toBe(true)
    expect(payload.quiz_count).toBe(12)
    expect(payload.articles[0]?.videos).toEqual([{ url: ' https://v ' }])
    expect(payload.include_code).toBe(false)
  })

  it('hydrates drafts and options from saved build request', () => {
    let n = 0
    const hydrated = hydrateLibraryFormFromRequest(
      {
        title: 'Docker',
        audience: 'devs',
        locale: 'ru',
        include_theory: true,
        include_quizzes: false,
        include_code: true,
        course_depth: 'deep',
        layout: 'phased',
        ignore_deviations: true,
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
    expect(hydrated.ignoreDeviations).toBe(true)
    expect(usableLibraryDrafts(hydrated.drafts)).toHaveLength(2)
  })

  it('builds resume payload with build_id only', () => {
    expect(
      buildResumeCoursePayload({
        buildId: '11111111-1111-1111-1111-111111111111',
        ignoreDeviations: true,
        codeSuitabilityAction: 'keep_code',
      }),
    ).toEqual({
      build_id: '11111111-1111-1111-1111-111111111111',
      ignore_deviations: true,
      code_suitability_action: 'keep_code',
    })
  })

  it('suggests realistic course scale from volume and outline beats', () => {
    expect(totalLibraryContentChars([{ content: '  ab  ' }, { content: 'cdef' }])).toBe(6)

    // 38k ≈ 9 слайдов — как типичный analyze, не 1 слайд / 1k символов.
    expect(suggestCourseScale(38_000, 'standard')).toEqual({
      theoryCount: 9,
      quizCount: 8,
      practiceCount: 3,
    })
    expect(suggestCourseScale(8_000, 'standard')).toEqual({
      theoryCount: 2,
      quizCount: 2,
      practiceCount: 1,
    })
    expect(suggestCourseScale(2_000, 'standard')).toEqual({
      theoryCount: 2,
      quizCount: 2,
      practiceCount: 1,
    })

    const sections = Array.from({ length: 9 }, (_, index) => {
      const body = 'текст '.repeat(700)
      return `## Тема ${index + 1}\n\n${body}`
    }).join('\n\n')
    const fromDrafts = suggestCourseScaleFromDrafts([{ content: sections }], 'standard')
    expect(fromDrafts.theoryCount).toBeGreaterThanOrEqual(7)
    expect(fromDrafts.theoryCount).toBeLessThanOrEqual(12)

    const deep = suggestCourseScale(20_000, 'deep')
    const light = suggestCourseScale(20_000, 'light')
    expect(deep.theoryCount).toBeGreaterThanOrEqual(suggestCourseScale(20_000, 'standard').theoryCount)
    expect(light.theoryCount).toBeLessThanOrEqual(suggestCourseScale(20_000, 'standard').theoryCount)
    expect(suggestCourseScale(200_000, 'deep').theoryCount).toBe(20)
    expect(suggestCourseScale(200_000, 'deep').practiceCount).toBe(7)
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
        easy: 'лёгкие',
        medium: 'нормальные',
        hard: 'сложные',
      }),
    ).toBe('3× лёгкие · 3× нормальные · 2× сложные')
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
