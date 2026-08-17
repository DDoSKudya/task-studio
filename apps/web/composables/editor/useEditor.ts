export function useEditor() {
  const config = useRuntimeConfig()
  const { request } = useApi()

  async function sendBeacon(
    event: 'open' | 'close',
    payload: { language: string; sessionId: string },
  ) {
    const params = new URLSearchParams({
      event,
      language: payload.language,
      session_id: payload.sessionId,
    })
    await request(`/v1/editor/events?${params.toString()}`, { method: 'POST' })
  }

  function apiBase() {
    return config.public.apiBase as string
  }

  return {
    apiBase,
    sendBeacon,
  }
}
