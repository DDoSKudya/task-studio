export type CoursePhase = 'study' | 'practice' | 'assess'

export type CourseOutlineLesson = {
  topicId: string
  phase: CoursePhase
  stepId: string
  title: string
  kind: string
  indexLabel: string
}

export type CourseOutlineModule = {
  topicId: string
  title: string
  index: number
  lessons: CourseOutlineLesson[]
}
