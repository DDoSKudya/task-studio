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

  async function fetchMe() {
    const response = await request<MeResponse>('/v1/auth/me')
    user.value = response.user
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
    await request('/v1/auth/logout', { method: 'POST' })
    user.value = null
  }

  return {
    user,
    fetchMe,
    login,
    register,
    logout,
  }
}
