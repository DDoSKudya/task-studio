const publicPaths = new Set(['/login', '/register', '/auth'])

export default defineNuxtRouteMiddleware(async (to) => {
  const { user, fetchMe } = useAuth()

  if (to.path === '/auth') {
    return navigateTo('/login', { replace: true })
  }

  if (publicPaths.has(to.path)) {
    if (!user.value) {
      try {
        await fetchMe()
      } catch {
        return
      }
    }
    if (user.value) {
      return navigateTo('/catalog')
    }
    return
  }

  if (user.value) {
    return
  }

  try {
    await fetchMe()
  } catch {
    return navigateTo('/login')
  }
})
