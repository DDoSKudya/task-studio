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
  started_at: string
  updated_at: string
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
}

export type SubmitResult = {
  attempt_id: string
  status?: 'completed' | 'pending'
  passed: boolean
  score: number
  feedback: string | null
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

export function useSessions() {
  const { request } = useApi()

  async function startSession(packVersionId: string) {
    return request<SessionState>('/v1/sessions', {
      method: 'POST',
      body: { pack_version_id: packVersionId },
    })
  }

  async function getSession(sessionId: string) {
    return request<SessionState>(`/v1/sessions/${sessionId}`)
  }

  async function getStep(sessionId: string) {
    return request<StepContent>(`/v1/sessions/${sessionId}/step`)
  }

  async function navigate(
    sessionId: string,
    payload: { topic: string; phase: SessionSummary['current_phase']; step: string },
  ) {
    return request<SessionState>(`/v1/sessions/${sessionId}/navigate`, {
      method: 'POST',
      body: payload,
    })
  }

  async function skipStudy(sessionId: string) {
    return request<SessionState>(`/v1/sessions/${sessionId}/skip-study`, {
      method: 'POST',
    })
  }

  async function submit(sessionId: string, submission: Record<string, unknown>) {
    return request<SubmitResult>(`/v1/sessions/${sessionId}/submit`, {
      method: 'POST',
      body: { submission },
    })
  }

  async function listAttempts(sessionId: string) {
    return request<AttemptInfo[]>(`/v1/sessions/${sessionId}/attempts`)
  }

  return {
    startSession,
    getSession,
    getStep,
    navigate,
    skipStudy,
    submit,
    listAttempts,
  }
}
