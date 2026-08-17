import { describe, expect, it } from 'vitest'
import {
  inferProviderMode,
  integrationDraftFromStored,
  isModelInList,
  coerceTutorModelSelection,
  modelAliases,
  normalizePlatformCredentials,
} from './tutorForm'

describe('settingsTutorForm', () => {
  it('infers provider mode from URL', () => {
    expect(inferProviderMode('')).toBe('ollama')
    expect(inferProviderMode('http://cursor-proxy:8015/v1')).toBe('cursor')
    expect(inferProviderMode('https://api.openai.com/v1')).toBe('external')
  })

  it('normalizes platform credentials', () => {
    expect(normalizePlatformCredentials(null)).toEqual({})
    expect(normalizePlatformCredentials({ token: 'abc', n: 1 })).toEqual({ token: 'abc' })
  })

  it('matches model aliases with :latest', () => {
    expect(modelAliases('qwen2.5:3b')).toEqual(['qwen2.5:3b', 'qwen2.5:3b:latest'])
    expect(isModelInList('qwen2.5:3b', ['qwen2.5:3b:latest'])).toBe(true)
    expect(isModelInList('missing', ['qwen2.5:3b'])).toBe(false)
  })

  it('builds editable integration drafts without ciphertext', () => {
    expect(
      integrationDraftFromStored(
        { username: 'u', password_encrypted: 'cipher', client_id: 'c' },
        ['username', 'password', 'client_id'],
      ),
    ).toEqual({ username: 'u', password: '', client_id: 'c' })
  })

  it('coerces invalid model selection after load', () => {
    expect(
      coerceTutorModelSelection({
        currentModel: 'gone',
        models: ['a', 'b'],
        providerMode: 'ollama',
      }),
    ).toBe('')
    expect(
      coerceTutorModelSelection({
        currentModel: 'gone',
        models: ['gpt-4o-mini', 'other'],
        providerMode: 'external',
      }),
    ).toBe('')
    expect(
      coerceTutorModelSelection({
        currentModel: 'auto',
        models: ['auto', 'composer'],
        providerMode: 'cursor',
      }),
    ).toBeNull()
    expect(
      coerceTutorModelSelection({
        currentModel: 'stale',
        models: [],
        providerMode: 'external',
      }),
    ).toBe('')
  })
})
