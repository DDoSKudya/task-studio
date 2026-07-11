export type TutorHintResponse = {
  hints: string[]
  source: 'fallback' | 'llm'
}

type TutorStreamEvent = {
  type: 'token' | 'done' | 'error'
  content?: string
}

export function useTutor() {
  const config = useRuntimeConfig()
  const { request } = useApi()

  async function getHints(sessionId: string, stepId: string) {
    const params = new URLSearchParams({ session_id: sessionId })
    return request<TutorHintResponse>(`/v1/tutor/hints/${stepId}?${params.toString()}`)
  }

  async function streamChat(
    sessionId: string,
    message: string,
    onEvent: (event: TutorStreamEvent) => void,
  ) {
    const response = await fetch(`${config.public.apiBase}/v1/tutor/chat`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw createError({ statusCode: response.status, data: error })
    }

    const reader = response.body?.getReader()
    if (!reader) {
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.startsWith('data:')) {
          continue
        }
        const payload = line.slice(5).trim()
        if (!payload) {
          continue
        }
        try {
          onEvent(JSON.parse(payload) as TutorStreamEvent)
        } catch {
          // ignore malformed chunks
        }
      }
    }
  }

  return { getHints, streamChat }
}
