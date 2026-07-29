import { describe, expect, it } from 'vitest'

import { resolveAssetIdSrc, resolveMediaSrc } from './url'

describe('mediaUrl', () => {
  it('resolves absolute asset paths via BFF', () => {
    expect(resolveAssetIdSrc('http://localhost/api', 'videos/intro.mp4')).toBe(
      'http://localhost/api/v1/media/videos/intro.mp4',
    )
    expect(resolveAssetIdSrc('http://localhost/api/', '/clips/a.mp4')).toBe(
      'http://localhost/api/v1/media/clips/a.mp4',
    )
  })

  it('keeps external URLs and prefixes root-relative ones', () => {
    expect(resolveMediaSrc('http://localhost/api', 'https://cdn.example/v.mp4')).toBe(
      'https://cdn.example/v.mp4',
    )
    expect(resolveMediaSrc('http://localhost/api', '/static/v.mp4')).toBe(
      'http://localhost/api/static/v.mp4',
    )
    expect(resolveMediaSrc('http://localhost/api', '  ')).toBe('')
  })
})
