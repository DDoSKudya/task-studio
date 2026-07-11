import type * as Monaco from 'monaco-editor'

export type GrammarDefinition = {
  language: string
  monarch: Monaco.languages.IMonarchLanguage
}

export async function loadGrammar(language: string): Promise<GrammarDefinition | null> {
  try {
    const module = await import(`../../../editor_grammars/${language}.json`)
    const payload = module.default ?? module
    if (!payload || typeof payload !== 'object') {
      return null
    }
    const record = payload as Record<string, unknown>
    const monarch = record.monarch
    if (!monarch || typeof monarch !== 'object') {
      return null
    }
    return {
      language,
      monarch: monarch as Monaco.languages.IMonarchLanguage,
    }
  } catch {
    return null
  }
}

export async function registerGrammar(
  monaco: typeof Monaco,
  language: string,
): Promise<boolean> {
  const grammar = await loadGrammar(language)
  if (!grammar) {
    return false
  }
  monaco.languages.register({ id: grammar.language })
  monaco.languages.setMonarchTokensProvider(grammar.language, grammar.monarch)
  return true
}
