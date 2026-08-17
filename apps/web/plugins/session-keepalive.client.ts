const ROTATE_EVERY_MS = 30 * 60 * 1000
const CHECK_EVERY_MS = 5 * 60 * 1000

export default defineNuxtPlugin(() => {
  const { user } = useAuth()
  const { rotateSession } = useApi()
  let lastRotate = Date.now()

  async function keepSessionAlive() {
    if (!user.value || document.visibilityState === 'hidden') {
      return
    }
    if (Date.now() - lastRotate < ROTATE_EVERY_MS) {
      return
    }
    lastRotate = Date.now()
    await rotateSession()
  }

  window.setInterval(() => void keepSessionAlive(), CHECK_EVERY_MS)
  document.addEventListener('visibilitychange', () => void keepSessionAlive())
})
