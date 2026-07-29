import type {
  AttemptInfo,
  SessionState,
  SessionSummary,
  StepContent,
  SubmitResult,
} from '~/utils/session'

export type {
  AttemptInfo,
  OutlineStep,
  OutlineTopic,
  PackPolicies,
  PhaseProgress,
  SessionState,
  SessionSummary,
  StepContent,
  StepNavTarget,
  SubmitResult,
} from '~/utils/session'

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
    payload: {
      topic: string
      phase: SessionSummary['current_phase']
      step: string
      complete_current?: boolean
    },
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

  async function listSessions() {
    return request<SessionSummary[]>('/v1/sessions')
  }

  return {
    startSession,
    getSession,
    getStep,
    navigate,
    skipStudy,
    submit,
    listAttempts,
    listSessions,
  }
}
