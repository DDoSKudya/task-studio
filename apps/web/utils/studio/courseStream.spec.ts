import { describe, expect, it } from 'vitest'
import {
  applyCourseStageEvent,
  consumeCourseSseBuffer,
  finalizeCourseStream,
  type CourseFromArticleResponse,
  type CourseStageEvent,
} from './courseStream'

describe('studioCourseStream', () => {
  it('applies done and error events', () => {
    const state: {
      doneResult: CourseFromArticleResponse | null
      gateEvent: CourseStageEvent | null
      streamError: string | null
    } = { doneResult: null, gateEvent: null, streamError: null }
    applyCourseStageEvent(
      {
        type: 'done',
        manifest: { title: 'x' },
        meta: { outcomes: ['a'], warnings: [], chapters: [] },
      },
      state,
    )
    expect(state.doneResult?.manifest).toEqual({ title: 'x' })
    applyCourseStageEvent({ type: 'error', message: 'boom' }, state)
    expect(finalizeCourseStream(state)).toEqual({ kind: 'error', message: 'boom' })
  })

  it('prefers consistency gate over done', () => {
    const gate = { type: 'consistency_gate' as const, message: 'check' }
    expect(
      finalizeCourseStream({
        doneResult: { manifest: {}, meta: { outcomes: [], warnings: [], chapters: [] } },
        gateEvent: gate,
        streamError: null,
      }),
    ).toEqual({ kind: 'consistency_gate', event: gate })
  })

  it('ignores ping keepalive frames', () => {
    const events: CourseStageEvent[] = []
    const state: {
      doneResult: CourseFromArticleResponse | null
      gateEvent: CourseStageEvent | null
      streamError: string | null
    } = { doneResult: null, gateEvent: null, streamError: null }
    consumeCourseSseBuffer(
      'data: {"type":"ping"}\n\ndata: {"type":"stage","stage":"theory","status":"running","progress":0.2,"message":"x"}\n\n',
      (event) => events.push(event),
      state,
    )
    expect(events).toHaveLength(1)
    expect(events[0]?.type).toBe('stage')
  })
})
