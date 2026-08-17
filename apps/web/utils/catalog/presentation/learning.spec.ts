import { describe, expect, it } from 'vitest'
import {
  emptyPackLearning,
  indexSessionsForPacks,
  matchSessionForPack,
  packLearningFromProgress,
  packLearningFromSession,
} from './learning'
import type { PackProgressItem, SessionSummary } from '../../session/types'

const base = (overrides: Partial<SessionSummary>): SessionSummary => ({
  id: 's1',
  pack_version_id: 'v1',
  pack_title: 'Intro',
  status: 'active',
  current_topic_id: 't',
  current_phase: 'study',
  current_step_id: 'st',
  started_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
  ...overrides,
})

describe('catalog/learning', () => {
  it('indexes sessions and matches packs', () => {
    const indexes = indexSessionsForPacks([
      base({ id: 'a', pack_version_id: 'v1', pack_title: 'Intro' }),
      base({ id: 'b', pack_version_id: 'v2', pack_title: 'Intro', status: 'abandoned' }),
    ])
    expect(matchSessionForPack({ version_id: 'v1', title: 'Intro' }, indexes)?.id).toBe('a')
    expect(matchSessionForPack({ version_id: 'missing', title: 'Intro' }, indexes)?.id).toBe('a')
  })

  it('builds learning snapshots', () => {
    expect(emptyPackLearning().progress).toBeNull()
    expect(
      packLearningFromSession({
        summary: base({ status: 'completed' }),
        detail: null,
        chapter: 'Done',
      }).progress,
    ).toBe(100)
  })

  it('builds learning from pack-progress item', () => {
    const item: PackProgressItem = {
      ...base({ id: 'p1' }),
      chapter_title: ' Chapter One ',
      progress_percent: 42,
    }
    expect(packLearningFromProgress(item, 'empty')).toEqual({
      progress: 42,
      phase: 'study',
      chapter: 'Chapter One',
      updatedAt: '2026-01-02T00:00:00Z',
      sessionId: 'p1',
      status: 'active',
    })
  })
})
