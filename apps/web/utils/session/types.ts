export type SessionSummary = {
  id: string
  pack_version_id: string
  pack_title: string
  status: 'active' | 'completed' | 'abandoned'
  current_topic_id: string
  current_phase: 'study' | 'practice' | 'assess'
  current_step_id: string
  started_at: string
  updated_at: string
}

export type PhaseProgress = {
  topic_id: string
  study_completed: boolean
  study_skipped: boolean
  practice_completed: boolean
  assess_completed: boolean
  assess_best_score: number | null
}

export type PackPolicies = {
  skip_study_allowed: boolean
  assess_without_practice: boolean
  assess_max_attempts: number | null
  assess_autocomplete: boolean
  tutor_enabled: boolean
  require_pass_to_advance?: boolean
  phase_order?: Array<'study' | 'practice' | 'assess'>
}

export type OutlineStep = {
  topic_id: string
  phase: SessionSummary['current_phase']
  step_id: string
  title: string
  kind: string
  index_label: string
}

export type OutlineTopic = {
  topic_id: string
  title: string
  index: number
  steps: OutlineStep[]
}

export type SessionState = {
  id: string
  pack_version_id: string
  pack_title: string
  status: SessionSummary['status']
  current_topic_id: string
  current_phase: SessionSummary['current_phase']
  current_step_id: string
  policies: PackPolicies
  phase_progress: PhaseProgress[]
  outline?: OutlineTopic[]
  passed_step_ids?: string[]
  completed_step_ids?: string[]
  started_at: string
  updated_at: string
}

export type StepNavTarget = {
  topic: string
  phase: SessionSummary['current_phase']
  step: string
}

export type StepContent = {
  topic_id: string
  phase: SessionSummary['current_phase']
  step_id: string
  kind: string
  title: string
  content: Record<string, unknown>
  editor: {
    runtime: string
    runtime_version: string
    template: string
    autocomplete: boolean
    lsp: string | null
  } | null
  tutor: {
    enabled: boolean
    mode: 'hint' | 'chat'
  } | null
  transitions: Record<string, string>
  prev_step?: StepNavTarget | null
  next_step?: StepNavTarget | null
}

export type SubmitResult = {
  attempt_id: string
  status?: 'completed' | 'pending'
  passed: boolean
  score: number
  feedback: string | null
  details?: Record<string, unknown>
  phase_completed: boolean
}

export type AttemptInfo = {
  id: string
  topic_id: string
  phase: SessionSummary['current_phase']
  step_id: string
  attempt_number: number
  submission: Record<string, unknown>
  result: Record<string, unknown> | null
  created_at: string
}
