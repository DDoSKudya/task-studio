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
  ollama_profile?: string | null
  recommended_models?: string[]
  course_pipeline?: 'compact' | 'full' | null
  active_course_model?: string | null
  active_chat_model?: string | null
  model_managed?: boolean
}

export type TutorStreamEvent = {
  type: 'token' | 'done' | 'error'
  content?: string
}
