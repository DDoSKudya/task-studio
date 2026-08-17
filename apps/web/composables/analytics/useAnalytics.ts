export type DailyProgressPoint = {
  day: string
  sessions_started: number
  steps_completed: number
}

export type ProgressResponse = {
  points: DailyProgressPoint[]
  total_sessions: number
  total_steps_completed: number
}

export type StudySkipEntry = {
  session_id: string
  pack_version_id: string
  pack_title: string
  topic_id: string
  skipped_at: string
}

export type SkipsResponse = {
  items: StudySkipEntry[]
  total: number
}

export type AttemptTimelineEntry = {
  attempt_id: string
  session_id: string
  pack_title: string
  topic_id: string
  phase: string
  step_id: string
  passed: boolean
  score: number
  created_at: string
}

export type AttemptsTimelineResponse = {
  items: AttemptTimelineEntry[]
  next_cursor: string | null
}

export function useAnalytics() {
  const { request } = useApi()

  async function fetchProgress(days = 30) {
    return request<ProgressResponse>(`/v1/analytics/progress?days=${days}`)
  }

  async function fetchSkips() {
    return request<SkipsResponse>('/v1/analytics/skips')
  }

  async function fetchAttempts(limit = 50) {
    return request<AttemptsTimelineResponse>(`/v1/analytics/attempts?limit=${limit}`)
  }

  return {
    fetchProgress,
    fetchSkips,
    fetchAttempts,
  }
}
