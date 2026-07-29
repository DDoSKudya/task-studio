import {
  CURSOR_PROXY_URL,
  OPENAI_PROVIDER_URL,
  type TutorProviderMode,
} from './tutorForm'

export type TutorProviderDraft = {
  providerUrl: string
  model: string
  apiKey: string
  hasStoredApiKey: boolean
}

export type TutorProviderProfilesState = Record<TutorProviderMode, TutorProviderDraft>

export function emptyProviderDraft(mode: TutorProviderMode): TutorProviderDraft {
  if (mode === 'cursor') {
    return {
      providerUrl: CURSOR_PROXY_URL,
      model: '',
      apiKey: '',
      hasStoredApiKey: false,
    }
  }
  if (mode === 'external') {
    return {
      providerUrl: OPENAI_PROVIDER_URL,
      model: '',
      apiKey: '',
      hasStoredApiKey: false,
    }
  }
  return {
    providerUrl: '',
    model: '',
    apiKey: '',
    hasStoredApiKey: false,
  }
}

export function emptyProviderProfiles(): TutorProviderProfilesState {
  return {
    ollama: emptyProviderDraft('ollama'),
    external: emptyProviderDraft('external'),
    cursor: emptyProviderDraft('cursor'),
  }
}

function coerceProfileRecord(raw: unknown): Partial<TutorProviderDraft> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return {}
  }
  const record = raw as Record<string, unknown>
  const patch: Partial<TutorProviderDraft> = {
    hasStoredApiKey: Boolean(record.api_key_encrypted),
  }

  if (typeof record.provider_url === 'string') {
    patch.providerUrl = record.provider_url
  }
  if (typeof record.model === 'string') {
    patch.model = record.model
  }
  return patch
}

export function providerProfilesFromSettings(
  record: Record<string, unknown>,
  activeMode: TutorProviderMode,
): TutorProviderProfilesState {
  const profiles = emptyProviderProfiles()
  const rawProfiles = record.provider_profiles
  if (rawProfiles && typeof rawProfiles === 'object' && !Array.isArray(rawProfiles)) {
    for (const mode of Object.keys(profiles) as TutorProviderMode[]) {
      const patch = coerceProfileRecord((rawProfiles as Record<string, unknown>)[mode])
      profiles[mode] = {
        ...profiles[mode],
        ...patch,
        apiKey: '',
      }
    }
  }


  profiles.cursor = {
    ...profiles.cursor,
    providerUrl: CURSOR_PROXY_URL,
  }

  const legacyUrl = typeof record.provider_url === 'string' ? record.provider_url : ''
  const legacyModel = typeof record.model === 'string' ? record.model : ''
  const legacyKey = Boolean(record.api_key_encrypted)
  if (!rawProfiles) {
    profiles[activeMode] = {
      ...profiles[activeMode],
      providerUrl: legacyUrl,
      model: legacyModel,
      hasStoredApiKey: legacyKey,
      apiKey: '',
    }
  }

  return profiles
}

export function snapshotActiveProvider(
  profiles: TutorProviderProfilesState,
  mode: TutorProviderMode,
  form: { providerUrl: string; model: string; apiKey: string },
  hasStoredApiKey: boolean,
): TutorProviderProfilesState {
  return {
    ...profiles,
    [mode]: {
      providerUrl: form.providerUrl,
      model: form.model,
      apiKey: form.apiKey,
      hasStoredApiKey,
    },
  }
}

export function buildProviderProfilesPayload(
  profiles: TutorProviderProfilesState,
  activeMode: TutorProviderMode,
  activeApiKey: string,
): Record<string, Record<string, string | null>> {
  const payload: Record<string, Record<string, string | null>> = {}
  for (const mode of Object.keys(profiles) as TutorProviderMode[]) {
    const draft = profiles[mode] ?? emptyProviderDraft(mode)
    const providerUrl = (draft.providerUrl ?? '').trim()
    const model = (draft.model ?? '').trim()
    const entry: Record<string, string | null> = {
      provider_url:
        mode === 'ollama'
          ? null
          : mode === 'cursor'
            ? CURSOR_PROXY_URL
            : providerUrl || null,
      model: model || null,
    }
    const apiKey = (mode === activeMode ? activeApiKey : draft.apiKey ?? '').trim()
    if (apiKey) {
      entry.api_key = apiKey
    }
    payload[mode] = entry
  }
  return payload
}
