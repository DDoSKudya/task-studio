export type StudioValidationIssue = {
  path: string
  message: string
}

export type StudioValidateResponse = {
  valid: boolean
  errors: StudioValidationIssue[]
}

export type StudioSuggestResponse = {
  suggestion: Record<string, unknown>
}

export function useStudio() {
  const config = useRuntimeConfig()
  const { request } = useApi()

  async function validateManifest(manifest: Record<string, unknown>) {
    return request<StudioValidateResponse>('/v1/studio/validate', {
      method: 'POST',
      body: { manifest },
    })
  }

  async function buildPack(manifest: Record<string, unknown>, assets: Array<{ path: string; content_base64: string }>) {
    const response = await fetch(`${config.public.apiBase}/v1/studio/build`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ manifest, assets }),
    })
    if (!response.ok) {
      const error = (await response.json().catch(() => ({}))) as { detail?: string }
      throw createError({
        statusCode: response.status,
        data: error,
      })
    }
    return response.blob()
  }

  async function suggestFragment(body: {
    context: string
    step_kind: string
    prompt: string
    manifest_fragment?: Record<string, unknown>
  }) {
    return request<StudioSuggestResponse>('/v1/studio/ai/suggest', {
      method: 'POST',
      body,
    })
  }

  return {
    validateManifest,
    buildPack,
    suggestFragment,
  }
}
