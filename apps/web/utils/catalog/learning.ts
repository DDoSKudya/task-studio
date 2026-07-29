import type { SessionState, SessionSummary } from '../session/types'
import { sessionProgressPercent } from '../session/learningProgress'

export type PackLearningSnapshot = {
  progress: number | null
  phase: SessionSummary['current_phase'] | null
  chapter: string
  updatedAt: string | null
  sessionId: string | null
  status: SessionSummary['status'] | null
}

export function indexSessionsForPacks(summaries: SessionSummary[]): {
  byVersion: Map<string, SessionSummary>
  byTitle: Map<string, SessionSummary>
} {
  const byVersion = new Map<string, SessionSummary>()
  const byTitle = new Map<string, SessionSummary>()
  for (const item of summaries) {
    if (item.status === 'abandoned') {
      continue
    }
    if (!byVersion.has(item.pack_version_id)) {
      byVersion.set(item.pack_version_id, item)
    }
    const titleKey = item.pack_title.trim().toLowerCase()
    if (titleKey && !byTitle.has(titleKey)) {
      byTitle.set(titleKey, item)
    }
  }
  return { byVersion, byTitle }
}

export function matchSessionForPack(
  pack: { version_id: string; title: string },
  indexes: {
    byVersion: Map<string, SessionSummary>
    byTitle: Map<string, SessionSummary>
  },
): SessionSummary | null {
  return (
    indexes.byVersion.get(pack.version_id)
    ?? indexes.byTitle.get(pack.title.trim().toLowerCase())
    ?? null
  )
}

export function emptyPackLearning(): PackLearningSnapshot {
  return {
    progress: null,
    phase: null,
    chapter: '',
    updatedAt: null,
    sessionId: null,
    status: null,
  }
}

export function packLearningFromSession(input: {
  summary: SessionSummary
  detail: SessionState | null
  chapter: string
}): PackLearningSnapshot {
  const progress = input.detail
    ? sessionProgressPercent(input.detail)
    : input.summary.status === 'completed'
      ? 100
      : null
  return {
    progress,
    phase: input.summary.current_phase,
    chapter: input.chapter,
    updatedAt: input.summary.updated_at,
    sessionId: input.summary.id,
    status: input.summary.status,
  }
}
