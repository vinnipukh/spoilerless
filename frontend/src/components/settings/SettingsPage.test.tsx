import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SettingsPage } from './SettingsPage'
import { getLLMSettings, updateLLMSettings } from '@/api/settings'

vi.mock('@/api/settings', () => ({
  getLLMSettings: vi.fn(),
  updateLLMSettings: vi.fn(),
}))

const defaultSettings = {
  provider: 'gemini' as const,
  model: 'gemini-2.5-flash',
  base_url: null,
  api_key_configured: true,
  api_key_masked: '••••7890',
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('SettingsPage', () => {
  it('loads and shows the current provider, model, and masked key', async () => {
    vi.mocked(getLLMSettings).mockResolvedValue(defaultSettings)
    render(<SettingsPage onBack={vi.fn()} />)

    expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument()
    expect(await screen.findByDisplayValue('gemini-2.5-flash')).toBeInTheDocument()
    expect(screen.getByText('API key configured (••••7890).')).toBeInTheDocument()
    // The stored key is never shown in full — only the masked placeholder.
    expect(screen.getByPlaceholderText(/••••7890 \(stored/)).toBeInTheDocument()
  })

  it('saves provider + api key via PUT and clears the key field', async () => {
    vi.mocked(getLLMSettings).mockResolvedValue({
      ...defaultSettings,
      api_key_configured: false,
      api_key_masked: null,
    })
    vi.mocked(updateLLMSettings).mockResolvedValue({
      ...defaultSettings,
      api_key_configured: true,
    })
    const user = userEvent.setup()
    render(<SettingsPage onBack={vi.fn()} />)

    const keyInput = await screen.findByLabelText('API key')
    await user.type(keyInput, 'AIzaSyNewGeminiKey')
    await user.click(screen.getByRole('button', { name: 'Save settings' }))

    expect(updateLLMSettings).toHaveBeenCalledWith({
      provider: 'gemini',
      api_key: 'AIzaSyNewGeminiKey',
      model: 'gemini-2.5-flash',
      base_url: null,
    })
    expect(await screen.findByText('API key configured (••••7890).')).toBeInTheDocument()
    expect(screen.getByLabelText('API key')).toHaveValue('')
  })

  it('shows the back button and calls onBack', async () => {
    vi.mocked(getLLMSettings).mockResolvedValue(defaultSettings)
    const onBack = vi.fn()
    const user = userEvent.setup()
    render(<SettingsPage onBack={onBack} />)

    await user.click(await screen.findByRole('button', { name: 'Back to graph' }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('keeps the form usable when loading fails — save stays enabled', async () => {
    vi.mocked(getLLMSettings).mockRejectedValue(new Error('Request failed.'))
    render(<SettingsPage onBack={vi.fn()} />)

    // The failure is surfaced but never blocks saving.
    expect(
      await screen.findByText('Could not load current settings (Request failed.). Save will overwrite them.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save settings' })).toBeEnabled()
  })
})
