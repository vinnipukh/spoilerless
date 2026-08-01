import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { getLLMSettings, updateLLMSettings } from '@/api/settings'
import type { LLMSettings, LLMProvider } from '@/types/settings'

type Props = {
  onBack: () => void
}

const inputClass = cn(
  'flex h-9 w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30',
  '[color-scheme:dark]',
)

export function SettingsPage({ onBack }: Props) {
  const [provider, setProvider] = useState<LLMProvider>('gemini')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [enabled, setEnabled] = useState(false)
  const [saved, setSaved] = useState<LLMSettings | null>(null)
  const [status, setStatus] = useState<'loading' | 'idle' | 'saving' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Loading is best-effort: a failed GET must never block saving (the PUT is
  // independent), so the form always ends up editable with sane defaults.
  useEffect(() => {
    let cancelled = false
    getLLMSettings()
      .then((settings) => {
        if (cancelled) return
        setProvider(settings.provider)
        setModel(settings.model ?? '')
        setBaseUrl(settings.base_url ?? '')
        setEnabled(settings.enabled)
        setSaved(settings)
        setStatus('idle')
      })
      .catch((error: unknown) => {
        if (cancelled) return
        // Keep the form editable — the previous config is simply unknown.
        setStatus('idle')
        setErrorMessage(
          error instanceof Error && error.message
            ? `Could not load current settings (${error.message}). Save will overwrite them.`
            : 'Could not load current settings. Save will overwrite them.',
        )
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSave() {
    setStatus('saving')
    setSaveError(null)
    setErrorMessage(null)
    try {
      const updated = await updateLLMSettings({
        provider,
        api_key: apiKey.trim() || undefined,
        model: model.trim() || null,
        base_url: baseUrl.trim() || null,
        enabled,
      })
      setSaved(updated)
      setApiKey('')
      setStatus('idle')
    } catch (error: unknown) {
      setStatus('idle')
      setSaveError(
        error instanceof Error && error.message
          ? `Failed to save LLM settings: ${error.message}`
          : 'Failed to save LLM settings.',
      )
    }
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
          <Button variant="ghost" size="sm" onClick={onBack} type="button">
            Back to graph
          </Button>
        </div>

        {status === 'loading' ? (
          <p className="mt-6 text-sm text-muted-foreground">Loading…</p>
        ) : (
          <div className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="settings-provider" className="text-sm font-medium">
                Provider
              </label>
              <Select value={provider} onValueChange={(value) => setProvider(value as LLMProvider)}>
                <SelectTrigger id="settings-provider" className="w-full">
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
              <input
                id="settings-api-key"
                type="password"
                autoComplete="off"
                className={inputClass}
                placeholder={
                  saved?.api_key_configured
                    ? `${saved.api_key_masked ?? 'configured'} (stored — leave blank to keep)`
                    : 'Paste your API key'
                }
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
              />
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
                  ? 'Optional — defaults to the official Gemini endpoint.'
                  : 'Required for OpenAI-compatible providers.'}
              </p>
            </div>

            <div className="flex items-center justify-between gap-3 rounded-lg border border-input px-3 py-2.5">
              <div className="flex min-w-0 flex-col gap-0.5">
                <label htmlFor="settings-enabled" className="text-sm font-medium">
                  Enable the chat assistant
                </label>
                <p className="text-xs text-muted-foreground">
                  {enabled
                    ? 'Chat and retrieval endpoints are active.'
                    : 'Disabled — chat returns LLM disabled. Turn this on after saving a key.'}
                </p>
              </div>
              <button
                id="settings-enabled"
                type="button"
                role="switch"
                aria-checked={enabled}
                onClick={() => setEnabled((current) => !current)}
                className={cn(
                  'relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:ring-offset-2',
                  enabled ? 'bg-primary' : 'bg-muted',
                )}
              >
                <span
                  className={cn(
                    'inline-block size-4 transform rounded-full bg-background shadow transition-transform',
                    enabled ? 'translate-x-[1.15rem]' : 'translate-x-0.5',
                  )}
                />
              </button>
            </div>

            {errorMessage && (
              <p className="text-sm text-destructive">{errorMessage}</p>
            )}
            {saveError && (
              <p className="text-sm text-destructive">{saveError}</p>
            )}
            {status === 'idle' && saved?.api_key_configured && (
              <p className="text-sm text-muted-foreground">
                API key configured ({saved.api_key_masked}).
              </p>
            )}

            <Button
              type="button"
              onClick={handleSave}
              disabled={status === 'saving'}
            >
              {status === 'saving' ? 'Saving…' : 'Save settings'}
            </Button>
          </div>
        )}
      </Card>
    </div>
  )
}
