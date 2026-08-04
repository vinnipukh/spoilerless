import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { getStoredLLMSettings, saveLLMSettings } from '@/lib/byok'
import type { LLMProvider } from '@/types/settings'

type Props = {
  onBack: () => void
}

const inputClass = cn(
  'flex h-9 w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-base transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30 md:text-sm',
  '[color-scheme:dark]',
)

// Heroicons outline eye / eye-slash (no emoji - svg-icon-replacements rule).
function EyeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-4 shrink-0" aria-hidden="true">
      <path d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
      <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-4 shrink-0" aria-hidden="true">
      <path d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
    </svg>
  )
}

export function SettingsPage({ onBack }: Props) {
  const [provider, setProvider] = useState<LLMProvider>('gemini')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [savedMessage, setSavedMessage] = useState<string | null>(null)

  // BYOK (AI-01/D-05): the key/base_url/model live ONLY in this browser's
  // localStorage - there is no settings-persistence endpoint anymore, so the
  // form is populated synchronously from localStorage and saving never
  // touches the network.
  useEffect(() => {
    const stored = getStoredLLMSettings()
    if (stored) {
      setProvider(stored.provider)
      setModel(stored.model)
      setBaseUrl(stored.base_url)
      setApiKey(stored.api_key)
    }
  }, [])

  function handleSave() {
    saveLLMSettings({ provider, api_key: apiKey, base_url: baseUrl, model })
    setSavedMessage('Saved to this browser.')
  }

  return (
    <div className="flex h-full items-start justify-center overflow-y-auto p-6">
      <Card className="w-full max-w-lg p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-heading text-xl">Settings</h2>
            <p className="text-sm text-muted-foreground">
              LLM provider configuration for the GraphRAG chat agent.
            </p>
          </div>
          <Button variant="ghost" size="sm" className="min-h-11" onClick={onBack} type="button">
            Back to graph
          </Button>
        </div>

        <div className="mt-4 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="settings-provider" className="text-sm font-medium">
              Provider
            </label>
            <Select value={provider} onValueChange={(value) => setProvider(value as LLMProvider)}>
              <SelectTrigger id="settings-provider" className="min-h-11 w-full">
                <SelectValue placeholder="Provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="gemini">Google Gemini</SelectItem>
                <SelectItem value="openai_compatible">OpenAI-compatible endpoint</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {provider === 'gemini'
                ? 'Uses the official Gemini REST API (generativelanguage.googleapis.com).'
                : 'Any OpenAI-compatible /chat/completions endpoint (base URL + model).'}
            </p>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="settings-api-key" className="text-sm font-medium">
              API key
            </label>
            <div className="relative">
              <input
                id="settings-api-key"
                type={showApiKey ? 'text' : 'password'}
                autoComplete="off"
                className={cn(inputClass, 'pr-11')}
                placeholder="Paste your API key"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowApiKey((visible) => !visible)}
                aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
                className="absolute right-0 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                {showApiKey ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="settings-model" className="text-sm font-medium">
              Model
            </label>
            <input
              id="settings-model"
              type="text"
              autoComplete="off"
              className={inputClass}
              placeholder={
                provider === 'gemini'
                  ? 'e.g. gemini-2.5-flash'
                  : 'e.g. deepseek-chat'
              }
              value={model}
              onChange={(event) => setModel(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="settings-base-url" className="text-sm font-medium">
              Base URL
            </label>
            <input
              id="settings-base-url"
              type="text"
              autoComplete="off"
              className={inputClass}
              placeholder={
                provider === 'gemini'
                  ? 'https://generativelanguage.googleapis.com'
                  : 'e.g. https://llm.example/v1'
              }
              value={baseUrl}
              onChange={(event) => setBaseUrl(event.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              {provider === 'gemini'
                ? 'Optional - defaults to the official Gemini endpoint.'
                : 'Required for OpenAI-compatible providers.'}
            </p>
          </div>

          {savedMessage && (
            <p className="text-sm text-muted-foreground">{savedMessage}</p>
          )}
          <p className="text-xs text-muted-foreground">
            Your API key never leaves this browser except as a per-request
            header sent to the endpoint you configure above.
          </p>

          <Button type="button" onClick={handleSave} className="min-h-11">
            Save settings
          </Button>
        </div>
      </Card>
    </div>
  )
}
