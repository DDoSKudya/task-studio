export type GradeResultLike = {
  passed: boolean
  feedback?: string | null
  details?: Record<string, unknown>
}

export function expectedChoiceIndex(details?: Record<string, unknown>): number | null {
  const expected = details?.expected
  return typeof expected === 'number' && Number.isInteger(expected) ? expected : null
}

export function sessionFeedbackMessage(
  result: GradeResultLike,
  t: (key: string) => string,
): string {
  const raw = (result.feedback || '').trim()
  const gradable = result.details?.gradable
  if (result.passed) {
    if (result.details?.checker === 'llm' && raw) {
      return raw
    }
    return t('session.feedback.passed')
  }
  if (gradable === false) {
    return t('session.feedback.ungradable')
  }
  if (raw.toLowerCase().includes('stepik')) {
    return t('session.feedback.stepikFailed')
  }
  return raw || t('session.feedback.failed')
}
