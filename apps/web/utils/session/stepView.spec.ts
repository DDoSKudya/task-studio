import { describe, expect, it } from 'vitest'
import {
  canAdvanceToNext,
  hasRichStudyBody,
  isCurrentLesson,
  isLessonDone,
  isStepPassedLocally,
  isTopicComplete,
  moduleDoneCount,
  outlineTopicsCompleted,
  quizChoicesFromContent,
  resolveStepVideoSrc,
  stepNeedsPassToAdvance,
  stepKindMark,
  taskRubricFromContent,
} from './stepView'
import type { OutlineTopic, PhaseProgress } from './types'

describe('sessionStepView', () => {
  it('tracks lesson completion against passed/completed sets', () => {
    const lesson = {
      topic_id: 't1',
      phase: 'study' as const,
      step_id: 's1',
      title: 'A',
      kind: 'theory',
      index_label: '1.1',
    }
    expect(isLessonDone(lesson, new Set(['s1']), new Set())).toBe(true)
    expect(isLessonDone(lesson, new Set(), new Set(['s1']))).toBe(true)
    expect(isLessonDone(lesson, new Set(), new Set())).toBe(false)
  })

  it('counts done lessons in a module', () => {
    const topic: OutlineTopic = {
      topic_id: 't1',
      title: 'Mod',
      index: 1,
      steps: [
        {
          topic_id: 't1',
          phase: 'study',
          step_id: 'a',
          title: 'A',
          kind: 'theory',
          index_label: '1.1',
        },
        {
          topic_id: 't1',
          phase: 'practice',
          step_id: 'b',
          title: 'B',
          kind: 'code',
          index_label: '1.2',
        },
      ],
    }
    expect(moduleDoneCount(topic, new Set(['a']), new Set())).toBe(1)
  })

  it('counts topic complete via phase_progress not per-step', () => {
    const topic: OutlineTopic = {
      topic_id: 't1',
      title: 'Docker',
      index: 1,
      steps: [
        {
          topic_id: 't1',
          phase: 'study',
          step_id: 'a',
          title: 'Theory',
          kind: 'theory',
          index_label: '1.1',
        },
        {
          topic_id: 't1',
          phase: 'practice',
          step_id: 'b',
          title: 'Lab',
          kind: 'code',
          index_label: '1.2',
        },
      ],
    }
    const progress: PhaseProgress[] = [
      {
        topic_id: 't1',
        study_completed: true,
        study_skipped: false,
        practice_completed: false,
        assess_completed: false,
        assess_best_score: null,
      },
    ]
    expect(isTopicComplete(topic, progress, new Set(), new Set())).toBe(false)
    progress[0].practice_completed = true
    expect(isTopicComplete(topic, progress, new Set(), new Set())).toBe(true)
    expect(
      outlineTopicsCompleted([topic], progress, new Set(), new Set()),
    ).toBe(1)
  })

  it('gates next navigation by pass policy', () => {
    expect(stepNeedsPassToAdvance(true, 'quiz')).toBe(true)
    expect(stepNeedsPassToAdvance(true, 'lab')).toBe(true)
    expect(stepNeedsPassToAdvance(true, 'theory')).toBe(false)
    expect(canAdvanceToNext({ hasNext: true, needsPass: true, passed: false })).toBe(false)
    expect(canAdvanceToNext({ hasNext: true, needsPass: true, passed: true })).toBe(true)
  })

  it('does not treat ungradable code as locally passed', () => {
    expect(
      isStepPassedLocally({
        stepId: 'c1',
        kind: 'code',
        passedStepIds: new Set(),
        quizReveal: null,
        codeReveal: { passed: false, gradable: false },
        taskReveal: null,
      }),
    ).toBe(false)
  })

  it('reads step content helpers', () => {
    expect(taskRubricFromContent({ rubric: '  ok  ' })).toBe('ok')
    expect(quizChoicesFromContent({ choices: ['a', 1, 'b'] })).toEqual(['a', 'b'])
    expect(hasRichStudyBody({ body_html: '<p>x</p>' })).toBe(true)
    expect(isCurrentLesson('t', 's', 't', 's')).toBe(true)
    expect(resolveStepVideoSrc({ url: 'https://cdn/v.mp4' }, 'http://api')).toBe('https://cdn/v.mp4')
  })

  it('localizes step kind marks via i18n', () => {
    const ruMarks: Record<string, string> = {
      'session.kindMark.theory': 'Т',
      'session.kindMark.quiz': 'В',
      'session.kindMark.code': 'З',
    }
    const t = (key: string) => ruMarks[key] ?? key
    const te = (key: string) => key in ruMarks
    expect(stepKindMark('theory', t, te)).toBe('Т')
    expect(stepKindMark('quiz', t, te)).toBe('В')
    expect(stepKindMark('code', t, te)).toBe('З')
    expect(stepKindMark('code', (k) => k, () => false)).toBe('C')
  })
})
