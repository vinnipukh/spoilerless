// BYOK-only settings shape (AI-01, D-05, D-06): the browser holds the LLM
// provider key/base_url/model in localStorage and forwards them per-request
// as X-LLM-* headers. The server no longer persists LLM settings from the
// frontend, so the old LLMSettings / LLMSettingsUpdate response types (with
// `enabled` and `system_prompt_language`) are gone.

// 'vllm' and 'ollama' are scaffolding: the backend already routes them
// through the OpenAI-compatible provider (same header shape), a dedicated
// integration can follow later without changing this type or the headers.
export type LLMProvider = 'gemini' | 'openai_compatible' | 'vllm' | 'ollama'

export type StoredLLMSettings = {
  provider: LLMProvider
  api_key: string
  base_url: string
  model: string
}
