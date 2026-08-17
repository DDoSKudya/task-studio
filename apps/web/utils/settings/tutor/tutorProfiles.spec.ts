import { describe, expect, it } from 'vitest'
import {
  buildProviderProfilesPayload,
  emptyProviderProfiles,
  providerProfilesFromSettings,
  snapshotActiveProvider,
} from './tutorProfiles'

describe('tutorProfiles', () => {
  it('keeps draft api keys when switching active provider snapshot', () => {
    let profiles = emptyProviderProfiles()
    profiles = snapshotActiveProvider(
      profiles,
      'cursor',
      { providerUrl: 'http://cursor-proxy:8080', model: 'composer-1', apiKey: 'cursor-secret' },
      false,
    )
    profiles = snapshotActiveProvider(
      profiles,
      'external',
      { providerUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini', apiKey: 'openai-secret' },
      false,
    )

    expect(profiles.cursor.apiKey).toBe('cursor-secret')
    expect(profiles.external.apiKey).toBe('openai-secret')

    const payload = buildProviderProfilesPayload(profiles, 'external', 'openai-secret')
    expect(payload.cursor.api_key).toBe('cursor-secret')
    expect(payload.external.api_key).toBe('openai-secret')
  })

  it('marks stored encrypted keys without exposing plaintext', () => {
    const profiles = providerProfilesFromSettings(
      {
        active_provider: 'cursor',
        provider_profiles: {
          cursor: {
            provider_url: 'http://cursor-proxy:8080',
            model: 'composer-1',
            api_key_encrypted: 'enc-cursor',
          },
          external: {
            provider_url: 'https://api.openai.com/v1',
            model: 'gpt-4o-mini',
            api_key_encrypted: 'enc-openai',
          },
        },
      },
      'cursor',
    )

    expect(profiles.cursor.hasStoredApiKey).toBe(true)
    expect(profiles.external.hasStoredApiKey).toBe(true)
    expect(profiles.cursor.apiKey).toBe('')
    expect(profiles.external.apiKey).toBe('')
  })

  it('keeps string defaults when profile fields are null from API', () => {
    const profiles = providerProfilesFromSettings(
      {
        provider_profiles: {
          cursor: {
            provider_url: null,
            model: null,
            api_key_encrypted: 'enc',
          },
          ollama: {
            provider_url: null,
            model: null,
          },
        },
      },
      'cursor',
    )

    expect(profiles.cursor.providerUrl).toBe('http://cursor-proxy:8015/v1')
    expect(profiles.cursor.model).toBe('')
    expect(profiles.ollama.providerUrl).toBe('')
    expect(profiles.ollama.model).toBe('')

    expect(() => buildProviderProfilesPayload(profiles, 'cursor', 'k')).not.toThrow()
    const payload = buildProviderProfilesPayload(profiles, 'cursor', 'k')
    expect(payload.cursor.api_key).toBe('k')
    expect(payload.cursor.model).toBeNull()
  })

  it('keeps cursor model when snapshotting the previous ollama draft', () => {
    let profiles = emptyProviderProfiles()
    profiles = snapshotActiveProvider(
      profiles,
      'cursor',
      { providerUrl: 'http://cursor-proxy:8015/v1', model: 'composer-1', apiKey: 'cursor-secret' },
      false,
    )
    profiles = snapshotActiveProvider(
      profiles,
      'ollama',
      { providerUrl: '', model: 'qwen2.5:7b', apiKey: '' },
      false,
    )

    expect(profiles.cursor.model).toBe('composer-1')
    expect(profiles.ollama.model).toBe('qwen2.5:7b')
  })

  it('forces cursor proxy URL even when a foreign endpoint was stored', () => {
    const profiles = providerProfilesFromSettings(
      {
        provider_profiles: {
          cursor: {
            provider_url: 'https://api.mistral.ai/v1',
            model: 'auto',
            api_key_encrypted: 'enc',
          },
        },
      },
      'cursor',
    )
    expect(profiles.cursor.providerUrl).toBe('http://cursor-proxy:8015/v1')
    const payload = buildProviderProfilesPayload(profiles, 'cursor', '')
    expect(payload.cursor.provider_url).toBe('http://cursor-proxy:8015/v1')
  })
})
