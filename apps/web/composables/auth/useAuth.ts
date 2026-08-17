export type AuthUser = {
  id: string
  email: string
  locale: string
  theme: string
}

export type MeResponse = {
  user: AuthUser
  settings: Record<string, unknown>
}

export function useAuth() {
  const { request } = useApi()
  const user = useState<AuthUser | null>('auth-user', () => null)
  const settings = useState<Record<string, unknown>>('auth-settings', () => ({}))

  async function fetchMe() {
    const response = await request<MeResponse>('/v1/auth/me')
    user.value = response.user
    settings.value = response.settings
    return response
  }

  async function login(email: string, password: string) {
    await request('/v1/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    await fetchMe()
  }

  async function register(email: string, password: string) {
    await request('/v1/auth/register', {
      method: 'POST',
      body: { email, password },
    })
    await fetchMe()
  }

  async function logout() {
    try {
      await request('/v1/auth/logout', { method: 'POST' })
    } catch {
      void 0
    }
    user.value = null
    settings.value = {}
    if (import.meta.client) {
      await navigateTo('/login')
    }
  }

  async function patchSettings(body: {
    locale?: string
    theme?: string
    settings?: Record<string, unknown>
  }) {
    const response = await request<MeResponse>('/v1/auth/me/settings', {
      method: 'PATCH',
      body,
    })
    user.value = response.user
    settings.value = response.settings
    return response
  }

  return {
    user,
    settings,
    fetchMe,
    login,
    register,
    logout,
    patchSettings,
  }
}
