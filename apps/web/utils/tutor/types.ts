export type TutorHintResponse = {
  hints: string[]
  source: 'fallback' | 'llm'
}

export type TutorLlmStatus = {
  ok: boolean
  provider: 'ollama' | 'external'
  detail: string
  models: string[]
  default_model: string | null
}

export type TutorStreamEvent = {
  type: 'token' | 'done' | 'error'
  content?: string
}
