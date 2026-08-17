import {
  COURSE_ERROR_PATTERNS,
  LEGACY_PROGRESS_PATTERNS,
} from './localizeProgressPatterns'

type CourseProgressMessageSource = {
  message?: string
  message_key?: string
  message_params?: Record<string, unknown>
}

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

  for (const rule of LEGACY_PROGRESS_PATTERNS) {
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
  const theoryShort = raw.match(
    /^sources supported (\d+) of (\d+) requested theory slides$/i,
  )
  if (theoryShort) {
    const translated = translateIfPresent(t, `${prefix}.theorySlidesShort`, {
      got: Number(theoryShort[1] || 0),
      wanted: Number(theoryShort[2] || 0),
    })
    if (translated) {
      return translated
    }
  }
  const thinCorpus = raw.match(
    /^corpus too thin for (\d+) theory slides; kept (\d+)$/i,
  )
  if (thinCorpus) {
    const translated = translateIfPresent(t, `${prefix}.theoryOutlineThinCorpus`, {
      wanted: Number(thinCorpus[1] || 0),
      got: Number(thinCorpus[2] || 0),
    })
    if (translated) {
      return translated
    }
  }
  const shortAfterExpand = raw.match(
    /^outline short after expand: (\d+) of (\d+) theory slides$/i,
  )
  if (shortAfterExpand) {
    const translated = translateIfPresent(t, `${prefix}.theoryOutlineShortAfterExpand`, {
      got: Number(shortAfterExpand[1] || 0),
      wanted: Number(shortAfterExpand[2] || 0),
    })
    if (translated) {
      return translated
    }
  }
  const polishCapacity = raw.match(/^book polish skipped capacity:\s*(.+)$/i)
  if (polishCapacity) {
    const translated = translateIfPresent(t, `${prefix}.bookPolishSkippedCapacity`, {
      id: polishCapacity[1] ?? '',
    })
    if (translated) {
      return translated
    }
  }
  const polishSkippedFor = raw.match(/^book polish skipped for\s+([^:]+):\s*(.+)$/i)
  if (polishSkippedFor) {
    const translated = translateIfPresent(t, `${prefix}.bookPolishSkippedFor`, {
      id: polishSkippedFor[1]?.trim() ?? '',
      reason: polishSkippedFor[2]?.trim() ?? '',
    })
    if (translated) {
      return translated
    }
  }
  const theoryQualityWeak = raw.match(
    /^theory quality gate weak after reinforce:\s*(.+?)\s*\((.+)\)$/i,
  )
  if (theoryQualityWeak) {
    const translated = translateIfPresent(t, `${prefix}.theoryQualityWeak`, {
      title: theoryQualityWeak[1]?.trim() ?? '',
      detail: theoryQualityWeak[2]?.trim() ?? '',
    })
    if (translated) {
      return translated
    }
  }
  const quizQualityWeak = raw.match(
    /^quiz quality gate weak after reinforce:\s*(.+?)\s*\((.+)\)$/i,
  )
  if (quizQualityWeak) {
    const translated = translateIfPresent(t, `${prefix}.quizQualityWeak`, {
      title: quizQualityWeak[1]?.trim() ?? '',
      detail: quizQualityWeak[2]?.trim() ?? '',
    })
    if (translated) {
      return translated
    }
  }
  const practiceQualityWeak = raw.match(
    /^practice quality gate weak after reinforce:\s*(.+?)\s*\((.+)\)$/i,
  )
  if (practiceQualityWeak) {
    const translated = translateIfPresent(t, `${prefix}.practiceQualityWeak`, {
      title: practiceQualityWeak[1]?.trim() ?? '',
      detail: practiceQualityWeak[2]?.trim() ?? '',
    })
    if (translated) {
      return translated
    }
  }
  const polishSkipped = raw.match(/^book polish skipped:\s*(.+)$/i)
  if (polishSkipped) {
    const translated = translateIfPresent(t, `${prefix}.bookPolishSkipped`, {
      reason: polishSkipped[1] ?? '',
    })
    if (translated) {
      return translated
    }
  }
  const localUnique = raw.match(
    /^local compiler: (\d+) unique topics from sources \(requested (\d+)\)$/i,
  )
  if (localUnique) {
    const translated = translateIfPresent(t, `${prefix}.localUniqueTopics`, {
      got: Number(localUnique[1] || 0),
      wanted: Number(localUnique[2] || 0),
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
  for (const rule of COURSE_ERROR_PATTERNS) {
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
