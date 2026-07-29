import { describe, expect, it } from 'vitest'
import { expectedChoiceIndex, sessionFeedbackMessage } from './feedback'

const t = (key: string) => key

describe('sessionFeedback', () => {
  it('reads integer expected choice', () => {
    expect(expectedChoiceIndex({ expected: 2 })).toBe(2)
    expect(expectedChoiceIndex({ expected: 1.5 })).toBeNull()
    expect(expectedChoiceIndex({})).toBeNull()
  })

  it('prefers llm feedback on pass', () => {
    expect(
      sessionFeedbackMessage(
        { passed: true, feedback: 'Nice', details: { checker: 'llm' } },
        t,
      ),
    ).toBe('Nice')
  })

  it('maps stepik fail and ungradable', () => {
    expect(
      sessionFeedbackMessage(
        { passed: false, feedback: 'Stepik denied', details: {} },
        t,
      ),
    ).toBe('session.feedback.stepikFailed')
    expect(
      sessionFeedbackMessage(
        { passed: false, feedback: '', details: { gradable: false } },
        t,
      ),
    ).toBe('session.feedback.ungradable')
  })
})
