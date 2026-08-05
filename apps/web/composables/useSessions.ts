import type {
  AttemptInfo,
  PackProgressItem,
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
  PackProgressItem,
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

  async function getAttempt(sessionId: string, attemptId: string) {
    return request<AttemptInfo>(`/v1/sessions/${sessionId}/attempts/${attemptId}`)
  }

  async function listSessions() {
    return request<SessionSummary[]>('/v1/sessions')
  }

  async function listPackProgress() {
    return request<PackProgressItem[]>('/v1/sessions/pack-progress')
  }

  return {
    startSession,
    getSession,
    getStep,
    navigate,
    skipStudy,
    submit,
    listAttempts,
    getAttempt,
    listSessions,
    listPackProgress,
  }
}
