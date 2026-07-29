import type { PhaseProgress, SessionState, SessionSummary } from '~/composables/useSessions'

function phaseWeight(row: PhaseProgress): number {
  if (row.assess_completed) {
    return 3
  }
  if (row.practice_completed) {
    return 2
  }
  if (row.study_completed || row.study_skipped) {
    return 1
  }
  return 0
}

export function sessionProgressPercent(session: SessionState): number {
  const rows = session.phase_progress
  if (!rows.length) {
    return 0
  }
  const done = rows.reduce((sum, row) => sum + phaseWeight(row), 0)
  return Math.round((done / (rows.length * 3)) * 100)
}

export function sortSessionsByActivity(sessions: SessionSummary[]): SessionSummary[] {
  return [...sessions].sort(
    (left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
  )
}

export function relativeTime(value: string, locale: string): string {
  const target = new Date(value).getTime()
  const deltaSeconds = Math.round((target - Date.now()) / 1000)
  const abs = Math.abs(deltaSeconds)
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })

  if (abs < 60) {
    return formatter.format(Math.round(deltaSeconds), 'second')
  }
  if (abs < 3600) {
    return formatter.format(Math.round(deltaSeconds / 60), 'minute')
  }
  if (abs < 86400) {
    return formatter.format(Math.round(deltaSeconds / 3600), 'hour')
  }
  return formatter.format(Math.round(deltaSeconds / 86400), 'day')
}
