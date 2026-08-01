

export type LlmModelCatalogEntry = {

  pattern: RegExp

  descKey: string

  preferred: boolean
}

export const LLM_MODEL_CATALOG: LlmModelCatalogEntry[] = [

  { pattern: /^qwen2\.5-coder(:|$)/i, descKey: 'qwenCoder', preferred: true },
  { pattern: /^qwen2\.5(:|$)/i, descKey: 'qwen25', preferred: true },
  { pattern: /^qwen3(:|$)/i, descKey: 'qwen25', preferred: true },
  { pattern: /^phi4-mini(:|$)/i, descKey: 'phi4Mini', preferred: true },
  { pattern: /^phi4(:|$)/i, descKey: 'phi4', preferred: true },
  { pattern: /^gemma2(:|$)/i, descKey: 'gemma2', preferred: true },
  { pattern: /^mistral(:|$)/i, descKey: 'mistralLocal', preferred: true },
  { pattern: /^llama3\.2(:|$)/i, descKey: 'llama32', preferred: false },
  { pattern: /^llama3\.1(:|$)/i, descKey: 'llama32', preferred: false },
  { pattern: /^codellama(:|$)/i, descKey: 'codeLlama', preferred: false },

  { pattern: /^gpt-4o-mini$/i, descKey: 'gpt4oMini', preferred: true },
  { pattern: /^gpt-4\.1-mini$/i, descKey: 'gpt41Mini', preferred: true },
  { pattern: /^gpt-4o$/i, descKey: 'gpt4o', preferred: true },
  { pattern: /^gpt-4\.1$/i, descKey: 'gpt41', preferred: true },
  { pattern: /^o4-mini$/i, descKey: 'o4Mini', preferred: true },
  { pattern: /^o3-mini$/i, descKey: 'o4Mini', preferred: true },
  { pattern: /^mistral-small/i, descKey: 'mistralSmall', preferred: true },
  { pattern: /^codestral/i, descKey: 'codestral', preferred: true },
  { pattern: /^mistral-medium/i, descKey: 'mistralMedium', preferred: false },
  { pattern: /^mistral-large/i, descKey: 'mistralLarge', preferred: false },

  { pattern: /^auto$/i, descKey: 'cursorAuto', preferred: true },
  { pattern: /^composer/i, descKey: 'composer', preferred: true },
  { pattern: /^claude-.*sonnet/i, descKey: 'claudeSonnet', preferred: true },
  { pattern: /^claude-.*haiku/i, descKey: 'claudeHaiku', preferred: true },
  { pattern: /^claude-.*opus/i, descKey: 'claudeOpus', preferred: false },
  { pattern: /^gemini-.*flash/i, descKey: 'geminiFlash', preferred: true },
  { pattern: /^gemini-.*pro/i, descKey: 'geminiPro', preferred: true },
  { pattern: /^gemini/i, descKey: 'geminiPro', preferred: false },
]

export function findCatalogEntry(modelId: string): LlmModelCatalogEntry | null {
  const cleaned = modelId.trim()
  if (!cleaned) {
    return null
  }
  return LLM_MODEL_CATALOG.find((entry) => entry.pattern.test(cleaned)) ?? null
}

function sortAlpha(models: string[]): string[] {
  return [...models].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
}

export function selectProjectModels(available: string[]): {
  models: string[]
  filteredToPreferred: boolean
} {
  const unique = sortAlpha(
    [...new Set(available.map((item) => item.trim()).filter(Boolean))],
  )
  const preferred = unique.filter((id) => findCatalogEntry(id)?.preferred)
  if (preferred.length > 0) {
    return { models: preferred, filteredToPreferred: true }
  }
  return { models: unique, filteredToPreferred: false }
}
