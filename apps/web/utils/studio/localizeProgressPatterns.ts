export type LegacyProgressPattern = {
  re: RegExp
  key: string
  params?: (match: RegExpMatchArray) => Record<string, string | number>
}

export const LEGACY_PROGRESS_PATTERNS: LegacyProgressPattern[] = [
  {
    re: /^Synthesizing one progressive syllabus from all sources$/i,
    key: 'analyzeRunning',
  },
  {
    re: /^Syllabus outline ready/i,
    key: 'analyzeOutlineReady',
  },
  {
    re: /^Enriching chapter:\s*(.+)$/i,
    key: 'analyzeEnriching',
    params: (m) => ({ title: m[1] ?? '' }),
  },
  {
    re: /^Outline ready$/i,
    key: 'analyzeDone',
  },
  {
    re: /^Expanding chapter:\s*(.+)$/i,
    key: 'theoryExpanding',
    params: (m) => ({ title: m[1] ?? '' }),
  },
  {
    re: /^Quality reinforce:\s*(.+)$/i,
    key: 'theoryQuality',
    params: (m) => ({ title: m[1] ?? '' }),
  },
  {
    re: /^Theory ready:\s*(.+)$/i,
    key: 'theoryReady',
    params: (m) => ({ title: m[1] ?? '' }),
  },
  {
    re: /^Polishing theory into one book voice$/i,
    key: 'polishRunning',
  },
  {
    re: /^Book polish applied to\s+(\d+)\s+chapter\(s\);\s*skipped\s+(\d+)$/i,
    key: 'polishPartial',
    params: (m) => ({ count: Number(m[1] || 0), skipped: Number(m[2] || 0) }),
  },
  {
    re: /^Book polish applied to\s+(\d+)\s+chapter/i,
    key: 'polishDone',
    params: (m) => ({ count: Number(m[1] || 0) }),
  },
  {
    re: /^Designing\s+(\d+)\s+knowledge-check quizzes$/i,
    key: 'quizzesDesigning',
    params: (m) => ({ count: Number(m[1] || 0) }),
  },
  {
    re: /^Prepared\s+(\d+)\s+quizzes$/i,
    key: 'quizzesPrepared',
    params: (m) => ({ count: Number(m[1] || 0) }),
  },
  {
    re: /^Building\s+(\d+)-step code ladder/i,
    key: 'codeBuilding',
    params: (m) => ({ count: Number(m[1] || 0) }),
  },
  {
    re: /^Prepared\s+(\d+)\s+code tasks$/i,
    key: 'codePrepared',
    params: (m) => ({ count: Number(m[1] || 0) }),
  },
  {
    re: /^Assembling and validating pack manifest$/i,
    key: 'assembleRunning',
  },
  {
    re: /^Course pack ready$/i,
    key: 'assembleDone',
  },
  {
    re: /^Course generation complete with incomplete book polish$/i,
    key: 'generationCompletePartial',
  },
  {
    re: /^Course generation complete$/i,
    key: 'generationComplete',
  },
]

export type CourseErrorPattern = {
  re: RegExp
  key: string
  params?: (match: RegExpMatchArray) => Record<string, string | number>
}

export const COURSE_ERROR_PATTERNS: CourseErrorPattern[] = [
  { re: /^no tutor provider configured$/i, key: 'noProvider' },
  { re: /^course generation returned no manifest$/i, key: 'noManifest' },
  { re: /^course generation produced no result$/i, key: 'noResult' },
  { re: /^course analyze returned no chapters$/i, key: 'noChapters' },
  { re: /^course quizzes stage returned too few items$/i, key: 'quizzesTooFew' },
  { re: /^course code stage returned too few tasks$/i, key: 'codeTooFew' },
  { re: /^no usable articles$/i, key: 'noArticles' },
  { re: /^article too short$/i, key: 'articleTooShort' },
  { re: /^page has no readable article text$/i, key: 'noReadableArticle' },
  { re: /^extracted article too short$/i, key: 'extractedTooShort' },
  { re: /^course generation produced no content steps$/i, key: 'noContentSteps' },
  { re: /^course generation failed$/i, key: 'generationFailed' },
  { re: /^invalid manifest$/i, key: 'invalidManifest' },
  { re: /^local syllabus has no teachable/i, key: 'noTeachableSyllabus' },
  { re: /^local theory failed/i, key: 'localTheoryFailed' },
  { re: /^local quiz failed/i, key: 'localQuizFailed' },
  {
    re: /^local practice failed for «([^»]+)»/i,
    key: 'localPracticeFailed',
    params: (match) => ({ title: match[1] ?? '' }),
  },
  { re: /^local practice failed/i, key: 'localPracticeFailed' },
  { re: /copied the excerpt instead of teaching/i, key: 'theoryCopiedExcerpt' },
  { re: /^book polish did not finish/i, key: 'polishUnfinished' },
  { re: /^course used template filler/i, key: 'templateFiller' },
  { re: /^course generation requires at least/i, key: 'modelTooSmall' },
  { re: /^ollama is missing a course-capable/i, key: 'courseModelMissing' },
  { re: /^ollama is not reachable/i, key: 'ollamaUnreachable' },
  { re: /network\s*error|failed to fetch|load failed|err_network|networkerror/i, key: 'network' },
]
