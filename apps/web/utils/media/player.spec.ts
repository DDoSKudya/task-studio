import { describe, expect, it } from 'vitest'
import {
  formatMediaTime,
  mediaProgressPercent,
  resolvePlaybackSrc,
  seekRatioFromClientX,
} from './player'

describe('mediaPlayer', () => {
  it('formats time and progress', () => {
    expect(formatMediaTime(65)).toBe('1:05')
    expect(formatMediaTime(3661)).toBe('1:01:01')
    expect(formatMediaTime(Number.NaN)).toBe('0:00')
    expect(mediaProgressPercent(30, 100)).toBe(30)
    expect(mediaProgressPercent(10, 0)).toBe(0)
  })

  it('resolves playback urls and scrub ratios', () => {
    expect(resolvePlaybackSrc('/v.mp4', 'https://app.example/')).toBe('https://app.example/v.mp4')
    expect(resolvePlaybackSrc('https://cdn/v.mp4', 'https://app.example/')).toBe('https://cdn/v.mp4')
    expect(seekRatioFromClientX(50, 0, 100)).toBe(0.5)
    expect(seekRatioFromClientX(-10, 0, 100)).toBe(0)
  })
})
