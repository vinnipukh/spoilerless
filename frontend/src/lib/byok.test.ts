import { beforeEach, describe, expect, it } from 'vitest'
import {
  BYOK_STORAGE_KEY,
  getLLMHeaders,
  getStoredLLMSettings,
  saveLLMSettings,
} from './byok'
import type { StoredLLMSettings } from '@/types/settings'

// Legacy key (pre-REBRAND-01) — kept as a literal so the read-compat
// migration is tested against the exact old storage key, not a re-export.
const LEGACY_BYOK_STORAGE_KEY = 'hdgraf:byok-llm-settings'

const settings: StoredLLMSettings = {
  provider: 'gemini',
  api_key: '  secret-key  ',
  base_url: ' https://generativelanguage.googleapis.com ',
  model: ' gemini-2.5-pro ',
}

beforeEach(() => {
  localStorage.clear()
})

describe('getStoredLLMSettings', () => {
  it('returns null when nothing is stored', () => {
    expect(getStoredLLMSettings()).toBeNull()
  })

  it('reads settings from the new key', () => {
    localStorage.setItem(BYOK_STORAGE_KEY, JSON.stringify(settings))
    expect(getStoredLLMSettings()).toEqual(settings)
  })

  it('migrates settings from the legacy key when the new key is absent (read-compat)', () => {
    localStorage.setItem(LEGACY_BYOK_STORAGE_KEY, JSON.stringify(settings))
    expect(getStoredLLMSettings()).toEqual(settings)
  })

  it('prefers the new key over the legacy key when both exist', () => {
    localStorage.setItem(BYOK_STORAGE_KEY, JSON.stringify({ ...settings, model: 'new-model' }))
    localStorage.setItem(LEGACY_BYOK_STORAGE_KEY, JSON.stringify(settings))
    expect(getStoredLLMSettings()?.model).toBe('new-model')
  })

  it('returns null when the legacy key holds malformed JSON', () => {
    localStorage.setItem(LEGACY_BYOK_STORAGE_KEY, 'not-json{')
    expect(getStoredLLMSettings()).toBeNull()
  })

  it('returns null when the legacy key holds an object missing required fields', () => {
    localStorage.setItem(LEGACY_BYOK_STORAGE_KEY, JSON.stringify({ provider: 'gemini' }))
    expect(getStoredLLMSettings()).toBeNull()
  })
})

describe('saveLLMSettings', () => {
  it('writes the new key with trimmed fields and removes the legacy key', () => {
    localStorage.setItem(LEGACY_BYOK_STORAGE_KEY, JSON.stringify(settings))

    saveLLMSettings(settings)

    expect(localStorage.getItem(BYOK_STORAGE_KEY)).toBe(
      JSON.stringify({
        provider: 'gemini',
        api_key: 'secret-key',
        base_url: 'https://generativelanguage.googleapis.com',
        model: 'gemini-2.5-pro',
      }),
    )
    expect(localStorage.getItem(LEGACY_BYOK_STORAGE_KEY)).toBeNull()
  })
})

describe('getLLMHeaders', () => {
  it('returns {} when no settings are stored', () => {
    expect(getLLMHeaders()).toEqual({})
  })

  it('returns {} when the stored api_key is whitespace-only', () => {
    localStorage.setItem(BYOK_STORAGE_KEY, JSON.stringify({ ...settings, api_key: '   ' }))
    expect(getLLMHeaders()).toEqual({})
  })

  it('returns the provider and key headers, plus base_url/model when non-blank', () => {
    localStorage.setItem(BYOK_STORAGE_KEY, JSON.stringify(settings))
    expect(getLLMHeaders()).toEqual({
      'X-LLM-Api-Key': 'secret-key',
      'X-LLM-Provider': 'gemini',
      'X-LLM-Base-URL': 'https://generativelanguage.googleapis.com',
      'X-LLM-Model': 'gemini-2.5-pro',
    })
  })

  it('omits base_url/model headers when blank', () => {
    localStorage.setItem(
      BYOK_STORAGE_KEY,
      JSON.stringify({ provider: 'gemini', api_key: 'k', base_url: '', model: '' }),
    )
    expect(getLLMHeaders()).toEqual({
      'X-LLM-Api-Key': 'k',
      'X-LLM-Provider': 'gemini',
    })
  })
})
