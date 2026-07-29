type CourseProgressMessageSource = {
  message?: string
  message_key?: string
  message_params?: Record<string, unknown>
}

const LEGACY_PATTERNS: Array<{
  re: RegExp
  key: string
  params?: (match: RegExpMatchArray) => Record<string, string | number>
}> = [
  {
    re: /^Checking topic fit and contradictions across articles$/i,
    key: 'consistencyChecking',
  },
  {
    re: /^Consistency check finished$/i,
    key: 'consistencyDone',
  },
  {
    re: /^Articles differ/i,
    key: 'consistencyGate',
  },
  {
    re: /^Synthesizing one progressive syllabus from all sources$/i,
    key: 'analyzeRunning',
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
    re: /^Theory ready:\s*(.+)$/i,
    key: 'theoryReady',
    params: (m) => ({ title: m[1] ?? '' }),
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
    re: /^Course generation complete$/i,
    key: 'generationComplete',
  },
]

const ERROR_PATTERNS: Array<{ re: RegExp; key: string }> = [
  { re: /^no tutor provider configured$/i, key: 'noProvider' },
  { re: /^course generation returned no manifest$/i, key: 'noManifest' },
  { re: /^course generation produced no result$/i, key: 'noResult' },
  { re: /^course analyze returned no chapters$/i, key: 'noChapters' },
  { re: /^course quizzes stage returned too few items$/i, key: 'quizzesTooFew' },
  { re: /^course code stage returned too few tasks$/i, key: 'codeTooFew' },
  { re: /^no usable articles$/i, key: 'noArticles' },
  { re: /^article too short$/i, key: 'articleTooShort' },
  { re: /^course generation produced no content steps$/i, key: 'noContentSteps' },
  { re: /^course generation failed$/i, key: 'generationFailed' },
  { re: /^invalid manifest$/i, key: 'invalidManifest' },
]

type TranslateFn = (key: string, params?: Record<string, unknown>) => string

function translateIfPresent(
  t: TranslateFn,
  i18nKey: string,
  params?: Record<string, unknown>,
): string | null {
  const translated = t(i18nKey, params)
  if (!translated || translated === i18nKey) {
    return null
  }

  const leaf = i18nKey.includes('.') ? i18nKey.slice(i18nKey.lastIndexOf('.') + 1) : i18nKey
  if (translated === leaf) {
    return null
  }
  return translated
}

export function localizeCourseProgressMessage(
  source: CourseProgressMessageSource,
  t: TranslateFn,
  _te?: (key: string) => boolean,
  prefix = 'courseBuild.messages',
): string {
  const key = source.message_key?.trim()
  if (key) {
    const translated = translateIfPresent(t, `${prefix}.${key}`, source.message_params ?? {})
    if (translated) {
      return translated
    }
  }

  const raw = (source.message ?? '').trim()
  if (!raw) {
    return ''
  }

  for (const rule of LEGACY_PATTERNS) {
    const match = raw.match(rule.re)
    if (!match) {
      continue
    }
    const translated = translateIfPresent(t, `${prefix}.${rule.key}`, rule.params?.(match) ?? {})
    if (translated) {
      return translated
    }
  }

  return raw
}

export function localizeCourseWarning(
  warning: string,
  t: TranslateFn,
  _te?: (key: string) => boolean,
  prefix = 'courseBuild.warningsMap',
): string {
  const raw = warning.trim()
  if (!raw) {
    return raw
  }
  if (raw === 'continued despite article deviations') {
    const translated = translateIfPresent(t, `${prefix}.continuedDespiteDeviations`)
    if (translated) {
      return translated
    }
  }
  const trimmed = raw.match(/^trimmed chapters to (\d+)$/i)
  if (trimmed) {
    const translated = translateIfPresent(t, `${prefix}.trimmedChapters`, {
      count: Number(trimmed[1] || 0),
    })
    if (translated) {
      return translated
    }
  }
  return raw
}

export function localizeCourseError(
  message: string,
  t: TranslateFn,
  prefix = 'courseBuild.errors',
): string {
  const raw = message.trim()
  if (!raw) {
    return raw
  }
  for (const rule of ERROR_PATTERNS) {
    if (!rule.re.test(raw)) {
      continue
    }
    const translated = translateIfPresent(t, `${prefix}.${rule.key}`)
    if (translated) {
      return translated
    }
  }
  return raw
}
