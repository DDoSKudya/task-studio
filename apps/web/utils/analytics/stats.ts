export type AnalyticsProgressPoint = {
  sessions_started: number
  steps_completed: number
}

export type AnalyticsAttemptLike = {
  passed: boolean
  pack_title: string
  topic_id: string
}

export type AnalyticsWeakSpot = {
  key: string
  title: string
  topicId: string
  failed: number
  total: number
  failRate: number
}

export function attemptPassStats(attempts: AnalyticsAttemptLike[]): {
  passed: number
  failed: number
  total: number
  passRate: number | null
} {
  const passed = attempts.filter((item) => item.passed).length
  const failed = attempts.length - passed
  const total = passed + failed
  return {
    passed,
    failed,
    total,
    passRate: total ? Math.round((passed / total) * 100) : null,
  }
}

export function countActiveDays(points: AnalyticsProgressPoint[]): number {
  return points.filter((point) => point.sessions_started > 0 || point.steps_completed > 0).length
}

export function stepsPerActiveDay(totalSteps: number, activeDays: number): number {
  if (!activeDays) {
    return 0
  }
  return Math.round(totalSteps / activeDays)
}

export function streakFromPoints(points: AnalyticsProgressPoint[]): number {
  if (!points.length) {
    return 0
  }
  let streak = 0
  for (let index = points.length - 1; index >= 0; index -= 1) {
    const point = points[index]
    if (point.sessions_started > 0 || point.steps_completed > 0) {
      streak += 1
      continue
    }
    if (streak > 0) {
      break
    }
  }
  return streak
}

export function weakSpotsFromAttempts(
  attempts: AnalyticsAttemptLike[],
  limit = 6,
): AnalyticsWeakSpot[] {
  const buckets = new Map<string, AnalyticsWeakSpot>()
  for (const attempt of attempts) {
    const key = `${attempt.pack_title || '—'}::${attempt.topic_id}`
    const current = buckets.get(key) ?? {
      key,
      title: attempt.pack_title || attempt.topic_id,
      topicId: attempt.topic_id,
      failed: 0,
      total: 0,
      failRate: 0,
    }
    current.total += 1
    if (!attempt.passed) {
      current.failed += 1
    }
    current.failRate = current.total ? Math.round((current.failed / current.total) * 100) : 0
    buckets.set(key, current)
  }
  return [...buckets.values()]
    .filter((item) => item.failed > 0)
    .sort((a, b) => b.failed - a.failed || b.failRate - a.failRate)
    .slice(0, limit)
}
