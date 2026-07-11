export type ApiErrorBody = {
  detail?: string | Array<{ msg?: string }>
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
}

export function useApi() {
  const config = useRuntimeConfig()

  async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
    const { body, ...rest } = init
    const headers = new Headers(rest.headers)
    const payload: RequestInit = { ...rest, headers, credentials: 'include' }

    if (body !== undefined) {
      if (body instanceof FormData) {
        payload.body = body
      } else {
        if (!headers.has('Content-Type')) {
          headers.set('Content-Type', 'application/json')
        }
        payload.body = JSON.stringify(body)
      }
    }

    const response = await fetch(`${config.public.apiBase}${path}`, payload)

    if (!response.ok) {
      const error = (await response.json().catch(() => ({}))) as ApiErrorBody
      throw createError({
        statusCode: response.status,
        data: error,
      })
    }

    if (response.status === 204) {
      return undefined as T
    }

    return (await response.json()) as T
  }

  return { request }
}
