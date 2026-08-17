export function useElapsedTimer() {
  const elapsedMs = ref(0)
  let timer: ReturnType<typeof setInterval> | null = null
  let startedAt = 0

  function stopTimer() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function startTimer() {
    stopTimer()
    startedAt = Date.now()
    elapsedMs.value = 0
    timer = setInterval(() => {
      elapsedMs.value = Date.now() - startedAt
    }, 250)
  }

  onBeforeUnmount(stopTimer)

  return {
    elapsedMs,
    startTimer,
    stopTimer,
  }
}
