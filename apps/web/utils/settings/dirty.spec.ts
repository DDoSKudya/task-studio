import { describe, expect, it } from 'vitest'
import {
  clonePlain,
  integrationDraftDirty,
  languagesMapDirty,
  requiredFieldsFilled,
  settingsFormDirty,
  tutorFormDirty,
} from './dirty'

describe('settingsDirty', () => {
  it('clones plain objects', () => {
    const src = { a: 1, nested: { b: 2 } }
    const copy = clonePlain(src)
    expect(copy).toEqual(src)
    copy.nested.b = 9
    expect(src.nested.b).toBe(2)
  })

  it('detects integration draft changes', () => {
    expect(integrationDraftDirty({ token: 'a' }, { token: 'a' })).toBe(false)
    expect(integrationDraftDirty({ token: 'b' }, { token: 'a' })).toBe(true)
  })

  it('detects language and tutor dirty flags', () => {
    expect(languagesMapDirty({ python: true }, { python: false }, ['python'])).toBe(true)
    expect(
      tutorFormDirty(
        { providerUrl: 'http://x', apiKey: '', dailyLimit: 1, model: 'm' },
        'ollama',
        { providerUrl: 'http://x', providerMode: 'ollama', dailyLimit: 1, model: 'm' },
      ),
    ).toBe(false)
    expect(
      tutorFormDirty(
        { providerUrl: 'http://x', apiKey: 'secret', dailyLimit: 1, model: 'm' },
        'ollama',
        { providerUrl: 'http://x', providerMode: 'ollama', dailyLimit: 1, model: 'm' },
      ),
    ).toBe(true)
  })

  it('checks required credential fields', () => {
    expect(requiredFieldsFilled(['token'], { token: '  x  ' })).toBe(true)
    expect(requiredFieldsFilled(['token'], { token: '   ' })).toBe(false)
    expect(
      requiredFieldsFilled(['username', 'password'], {
        username: 'u',
        password_encrypted: 'cipher',
      }),
    ).toBe(true)
    expect(
      requiredFieldsFilled(['username', 'password'], {
        username: 'u',
      }),
    ).toBe(false)
  })

  it('aggregates settings dirty state', () => {
    expect(
      settingsFormDirty({
        tutorDirty: false,
        autocomplete: true,
        baselineAutocomplete: true,
        mode: 'full',
        baselineMode: 'full',
        languagesDirty: false,
        integrationDrafts: {},
        baselineIntegrations: {},
      }),
    ).toBe(false)
    expect(
      settingsFormDirty({
        tutorDirty: false,
        autocomplete: true,
        baselineAutocomplete: true,
        mode: 'full',
        baselineMode: 'full',
        languagesDirty: false,
        integrationDrafts: { stepik: { token: '1' } },
        baselineIntegrations: {},
      }),
    ).toBe(true)
  })
})
