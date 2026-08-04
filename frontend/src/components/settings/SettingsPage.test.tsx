import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SettingsPage } from './SettingsPage'
import { BYOK_STORAGE_KEY } from '@/lib/byok'

const storedSettings = {
  provider: 'gemini' as const,
  api_key: 'AIzaStoredKey',
  base_url: '',
  model: 'gemini-2.5-flash',
}

function seedStoredSettings(settings: typeof storedSettings) {
  localStorage.setItem(BYOK_STORAGE_KEY, JSON.stringify(settings))
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('SettingsPage', () => {
  it('populates the form from stored localStorage settings on mount', async () => {
    seedStoredSettings(storedSettings)
    render(<SettingsPage onBack={vi.fn()} />)

    expect(await screen.findByDisplayValue('gemini-2.5-flash')).toBeInTheDocument()
    expect(screen.getByLabelText('API key')).toHaveValue('AIzaStoredKey')
  })

  it('saves provider + api key to localStorage only - no network request fires', async () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    const user = userEvent.setup()
    render(<SettingsPage onBack={vi.fn()} />)

    await user.type(await screen.findByLabelText('API key'), 'AIzaSyNewGeminiKey')
    await user.click(screen.getByRole('button', { name: 'Save settings' }))

    expect(await screen.findByText('Saved to this browser.')).toBeInTheDocument()
    // BYOK contract: the key is written to localStorage, never sent over the
    // network (no settings-persistence endpoint exists anymore).
    expect(fetchSpy).not.toHaveBeenCalled()
    const stored = JSON.parse(localStorage.getItem(BYOK_STORAGE_KEY) ?? 'null')
    expect(stored).toMatchObject({
      provider: 'gemini',
      api_key: 'AIzaSyNewGeminiKey',
    })
  })

  it('trims whitespace from all fields before storing', async () => {
    const user = userEvent.setup()
    render(<SettingsPage onBack={vi.fn()} />)

    await user.type(await screen.findByLabelText('API key'), '  sk-browser-key  ')
    await user.type(screen.getByLabelText('Model'), '  deepseek-chat  ')
    await user.type(screen.getByLabelText('Base URL'), '  https://llm.example/v1  ')
    await user.click(screen.getByRole('button', { name: 'Save settings' }))

    const stored = JSON.parse(localStorage.getItem(BYOK_STORAGE_KEY) ?? 'null')
    expect(stored).toMatchObject({
      api_key: 'sk-browser-key',
      model: 'deepseek-chat',
      base_url: 'https://llm.example/v1',
    })
  })

  it('reveals and hides the API key via the show/hide toggle', async () => {
    const user = userEvent.setup()
    render(<SettingsPage onBack={vi.fn()} />)

    const keyInput = await screen.findByLabelText('API key')
    expect(keyInput).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: 'Show API key' }))
    expect(keyInput).toHaveAttribute('type', 'text')

    await user.click(screen.getByRole('button', { name: 'Hide API key' }))
    expect(keyInput).toHaveAttribute('type', 'password')
  })

  it('does not render the retired enable-toggle or assistant-language fields', async () => {
    render(<SettingsPage onBack={vi.fn()} />)

    expect(screen.queryByRole('switch')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Assistant language')).not.toBeInTheDocument()
  })

  it('shows the privacy copy about the key never leaving the browser', async () => {
    render(<SettingsPage onBack={vi.fn()} />)

    expect(
      await screen.findByText(/never leaves this browser except as a per-request header/i),
    ).toBeInTheDocument()
  })

  it('shows the back button and calls onBack', async () => {
    const onBack = vi.fn()
    const user = userEvent.setup()
    render(<SettingsPage onBack={onBack} />)

    await user.click(await screen.findByRole('button', { name: 'Back to graph' }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })
})
