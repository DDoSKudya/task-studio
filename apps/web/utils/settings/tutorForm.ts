export type TutorProviderMode = 'ollama' | 'external' | 'cursor'

export const EDITOR_RUNTIMES = ['python', 'javascript', 'go', 'sql'] as const
export const OPENAI_PROVIDER_URL = 'https://api.openai.com/v1'
export const OPENAI_DEFAULT_MODEL = 'gpt-4o-mini'
export const CURSOR_PROXY_URL = 'http://cursor-proxy:8015/v1'
export const CURSOR_DEFAULT_MODEL = 'auto'

export function defaultLanguageMap(): Record<string, boolean> {
  return Object.fromEntries(EDITOR_RUNTIMES.map((runtime) => [runtime, true]))
}

export function normalizePlatformCredentials(raw: unknown): Record<string, string> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return {}
  }
  const credentials: Record<string, string> = {}
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof value === 'string') {
      credentials[key] = value
    }
  }
  return credentials
}


export function integrationDraftFromStored(
  stored: Record<string, string>,
  fields: string[],
): Record<string, string> {
  const draft: Record<string, string> = {}
  for (const field of fields) {
    const plain = stored[field]
    draft[field] = typeof plain === 'string' && !field.endsWith('_encrypted') ? plain : ''
  }
  return draft
}

export function inferProviderMode(url: string): TutorProviderMode {
  const cleaned = url.trim().toLowerCase()
  if (!cleaned) {
    return 'ollama'
  }
  if (cleaned.includes('cursor-proxy')) {
    return 'cursor'
  }
  return 'external'
}

export function modelAliases(name: string): string[] {
  const cleaned = name.trim()
  if (!cleaned) {
    return []
  }
  return cleaned.endsWith(':latest')
    ? [cleaned, cleaned.slice(0, -':latest'.length)]
    : [cleaned, `${cleaned}:latest`]
}

export function isModelInList(wanted: string, models: string[]): boolean {
  if (!wanted.trim()) {
    return true
  }
  const wantedSet = new Set(modelAliases(wanted))
  return models.some((item) => modelAliases(item).some((alias) => wantedSet.has(alias)))
}


export function coerceTutorModelSelection(input: {
  currentModel: string
  models: string[]
  providerMode: TutorProviderMode
  cursorDefault?: string
  openaiDefault?: string
}): string | null {
  const { currentModel, models } = input
  if (!models.length) {
    return currentModel ? '' : null
  }
  if (!currentModel || isModelInList(currentModel, models)) {
    return null
  }

  return ''
}

