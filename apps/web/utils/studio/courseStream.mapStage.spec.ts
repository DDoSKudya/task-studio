import { describe, expect, it } from 'vitest'
import { mapCourseStageToUi } from './courseStream'

describe('mapCourseStageToUi', () => {
  it('maps topic_bundle onto theory chip', () => {
    expect(mapCourseStageToUi('topic_bundle')).toBe('theory')
  })

  it('maps code_suitability onto analyze chip', () => {
    expect(mapCourseStageToUi('code_suitability')).toBe('analyze')
  })

  it('maps leftover consistency stage onto analyze', () => {
    expect(mapCourseStageToUi('consistency')).toBe('analyze')
  })

  it('passes through known stages', () => {
    expect(mapCourseStageToUi('theory')).toBe('theory')
    expect(mapCourseStageToUi('polish')).toBe('polish')
    expect(mapCourseStageToUi('quizzes')).toBe('quizzes')
  })
})
