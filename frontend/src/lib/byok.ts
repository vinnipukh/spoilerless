// BYOK (bring-your-own-key) LLM settings, frontend half of D-06 (AI-01):
// the provider key/base_url/model live ONLY in this browser's localStorage
// under 'spoilerless:byok-llm-settings' and travel per-request as X-LLM-* headers.
// The key never leaves this browser except as a request header to the user's
// configured endpoint - nothing here touches the network, and no
// settings-persistence endpoint is involved (AI-01, D-05).
import type { StoredLLMSettings } from '@/types/settings'

export const BYOK_STORAGE_KEY = 'spoilerless:byok-llm-settings'

// Legacy key (pre-REBRAND-01). getStoredLLMSettings falls back to it once when
// the new key is absent so existing BYOK settings survive the rename;
// saveLLMSettings removes it after writing the new key (T-09-01-02).
const LEGACY_BYOK_STORAGE_KEY = 'hdgraf:byok-llm-settings'

function readKey(key: string): StoredLLMSettings | null {
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null) return null
    const candidate = parsed as Partial<StoredLLMSettings>
    if (typeof candidate.provider !== 'string' || typeof candidate.api_key !== 'string') {
      return null
    }
    return {
      provider: candidate.provider as StoredLLMSettings['provider'],
      api_key: candidate.api_key,
      base_url: typeof candidate.base_url === 'string' ? candidate.base_url : '',
      model: typeof candidate.model === 'string' ? candidate.model : '',
    }
  } catch {
    return null
  }
}

/**
 * Read the stored BYOK settings from localStorage. Absent or malformed
 * storage returns null and never throws - the settings form must stay
 * usable regardless of what is (or is not) in the browser.
 */
export function getStoredLLMSettings(): StoredLLMSettings | null {
  // REBRAND-01 read-compat migration: prefer the new key, fall back to the
  // legacy key once so settings saved before the rename are not lost.
  return readKey(BYOK_STORAGE_KEY) ?? readKey(LEGACY_BYOK_STORAGE_KEY)
}

/**
 * Persist the BYOK settings, trimming all three free-text fields on write
 * (matches the backend's whitespace-only-key rejection). The legacy key is
 * removed once the new key is written, completing the one-time migration.
 */
export function saveLLMSettings(settings: StoredLLMSettings): void {
  const trimmed: StoredLLMSettings = {
    provider: settings.provider,
    api_key: settings.api_key.trim(),
    base_url: settings.base_url.trim(),
    model: settings.model.trim(),
  }
  window.localStorage.setItem(BYOK_STORAGE_KEY, JSON.stringify(trimmed))
  window.localStorage.removeItem(LEGACY_BYOK_STORAGE_KEY)
}

/**
 * Headers for chat requests (D-06): X-LLM-Api-Key and X-LLM-Provider always
 * (together they're enough for Gemini - no base_url needed), plus
 * X-LLM-Base-URL / X-LLM-Model when non-blank. A missing or whitespace-only
 * key returns {} so the backend falls back to its own config and the key is
 * never sent anywhere.
 */
export function getLLMHeaders(): Record<string, string> {
  const settings = getStoredLLMSettings()
  if (!settings) return {}
  const apiKey = settings.api_key.trim()
  if (!apiKey) return {}
  const headers: Record<string, string> = {
    'X-LLM-Api-Key': apiKey,
    'X-LLM-Provider': settings.provider,
  }
  const baseUrl = settings.base_url.trim()
  const model = settings.model.trim()
  if (baseUrl) headers['X-LLM-Base-URL'] = baseUrl
  if (model) headers['X-LLM-Model'] = model
  return headers
}
