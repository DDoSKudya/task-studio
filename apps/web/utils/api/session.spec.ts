import { describe, expect, it } from 'vitest'

import { readSetCookieHeaders, shouldRotateSession } from './session'

describe('readSetCookieHeaders', () => {
  it('returns every cookie when runtime exposes getSetCookie', () => {
    const headers = new Headers()
    headers.append('set-cookie', 'studio_access_token=one; Path=/')
    headers.append('set-cookie', 'other=two; Path=/')

    expect(readSetCookieHeaders(headers)).toHaveLength(2)
  })

  it('returns empty list when upstream sent no cookie', () => {
    expect(readSetCookieHeaders(new Headers())).toEqual([])
  })
})

describe('shouldRotateSession', () => {
  it('rotates once on a client 401 for a business endpoint', () => {
    expect(
      shouldRotateSession({
        path: '/v1/studio/ai/fetch-article-from-url',
        statusCode: 401,
        retried: false,
        onClient: true,
      }),
    ).toBe(true)
  })

  it('never retries the auth endpoints themselves', () => {
    expect(
      shouldRotateSession({
        path: '/v1/auth/me',
        statusCode: 401,
        retried: false,
        onClient: true,
      }),
    ).toBe(false)
  })

  it('skips a second attempt and non-401 failures', () => {
    const base = { path: '/v1/catalog', onClient: true }

    expect(shouldRotateSession({ ...base, statusCode: 401, retried: true })).toBe(false)
    expect(shouldRotateSession({ ...base, statusCode: 502, retried: false })).toBe(false)
  })

  it('does nothing during server rendering', () => {
    expect(
      shouldRotateSession({
        path: '/v1/catalog',
        statusCode: 401,
        retried: false,
        onClient: false,
      }),
    ).toBe(false)
  })
})
