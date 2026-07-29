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

  it('flushes a final SSE frame without trailing newline', () => {
    const events: CourseStageEvent[] = []
    const state: {
      doneResult: CourseFromArticleResponse | null
      gateEvent: CourseStageEvent | null
      streamError: string | null
    } = { doneResult: null, gateEvent: null, streamError: null }
    const rest = consumeCourseSseBuffer(
      'data: {"type":"done","progress":1,"manifest":{"title":"T"},"meta":{"outcomes":[],"warnings":[],"chapters":[]}}',
      (event) => events.push(event),
      state,
    )
    expect(rest.startsWith('data:')).toBe(true)
    const flushed = consumeCourseSseBuffer(`${rest}\n`, (event) => events.push(event), state)
    expect(flushed).toBe('')
    expect(events).toHaveLength(1)
    expect(state.doneResult?.manifest).toEqual({ title: 'T' })
  })
})
