import { describe, expect, it } from 'vitest'
import {
  attemptPassStats,
  countActiveDays,
  stepsPerActiveDay,
  streakFromPoints,
  weakSpotsFromAttempts,
} from './stats'

describe('analyticsStats', () => {
  it('computes pass rate', () => {
    expect(
      attemptPassStats([
        { passed: true, pack_title: 'A', topic_id: 't' },
        { passed: false, pack_title: 'A', topic_id: 't' },
      ]),
    ).toEqual({ passed: 1, failed: 1, total: 2, passRate: 50 })
  })

  it('counts active days and streak', () => {
    const points = [
      { sessions_started: 0, steps_completed: 0 },
      { sessions_started: 1, steps_completed: 0 },
      { sessions_started: 0, steps_completed: 2 },
    ]
    expect(countActiveDays(points)).toBe(2)
    expect(streakFromPoints(points)).toBe(2)
    expect(stepsPerActiveDay(10, 2)).toBe(5)
  })

  it('ranks weak spots', () => {
    const spots = weakSpotsFromAttempts([
      { passed: false, pack_title: 'Pack', topic_id: 'a' },
      { passed: false, pack_title: 'Pack', topic_id: 'a' },
      { passed: false, pack_title: 'Pack', topic_id: 'b' },
      { passed: true, pack_title: 'Pack', topic_id: 'b' },
    ])
    expect(spots[0]?.topicId).toBe('a')
    expect(spots[0]?.failed).toBe(2)
  })
})
