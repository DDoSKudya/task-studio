export const EDITOR_RUNTIMES = ['python', 'javascript', 'go', 'sql'] as const

export type EditorMode = 'full' | 'syntax_only'

export type EditorLanguageSettings = {
  enabled: boolean
}

export type EditorSettings = {
  autocomplete: boolean
  mode: EditorMode
  languages: Record<string, EditorLanguageSettings>
}

export type EditorPolicyInput = {
  editorSettings: EditorSettings
  phase: 'study' | 'practice' | 'assess'
  packAutocomplete: boolean
  runtime: string
  lspId: string | null | undefined
}

const DEFAULT_EDITOR_SETTINGS: EditorSettings = {
  autocomplete: true,
  mode: 'full',
  languages: {},
}

export function parseEditorSettings(raw: Record<string, unknown> | undefined): EditorSettings {
  const editor = raw?.editor
  if (!editor || typeof editor !== 'object' || Array.isArray(editor)) {
    return DEFAULT_EDITOR_SETTINGS
  }
  const blob = editor as Record<string, unknown>
  const languages: Record<string, EditorLanguageSettings> = {}
  const rawLanguages = blob.languages
  if (rawLanguages && typeof rawLanguages === 'object' && !Array.isArray(rawLanguages)) {
    for (const [key, value] of Object.entries(rawLanguages)) {
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        languages[key] = { enabled: (value as { enabled?: boolean }).enabled !== false }
      }
    }
  }
  return {
    autocomplete: blob.autocomplete !== false,
    mode: blob.mode === 'syntax_only' ? 'syntax_only' : 'full',
    languages,
  }
}

export function shouldConnectLsp(input: EditorPolicyInput): boolean {
  if (!input.lspId) {
    return false
  }
  if (input.editorSettings.mode === 'syntax_only') {
    return false
  }
  if (!input.editorSettings.autocomplete) {
    return false
  }
  if (input.phase === 'assess' && !input.packAutocomplete) {
    return false
  }
  const language = input.editorSettings.languages[input.runtime]
  if (language && !language.enabled) {
    return false
  }
  return true
}

export function buildLspWebSocketUrl(apiBase: string, lspId: string, sessionId: string): string {
  const httpBase = apiBase.replace(/\/$/, '')
  const wsBase = httpBase.replace(/^http/, 'ws')
  const params = new URLSearchParams({ session_id: sessionId })
  return `${wsBase}/v1/lsp/${lspId}?${params.toString()}`
}
