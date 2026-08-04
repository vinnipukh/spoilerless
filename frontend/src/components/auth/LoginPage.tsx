import { useCallback, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/providers/useAuth'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential: string }) => void
            context?: string
            ux_mode?: string
            auto_select?: boolean
          }) => void
          renderButton: (
            element: HTMLElement | null,
            options: { theme?: string; size?: string; shape?: string; text?: string; logo_alignment?: string; width?: string },
          ) => void
          prompt: (moment: () => void) => void
          cancel: () => void
          disableAutoSelect: () => void
        }
      }
    }
  }
}

export function LoginPage() {
  const { login, state } = useAuth()
  const buttonContainerRef = useRef<HTMLDivElement>(null)
  const initRef = useRef(false)

  // Stable callback — never recreated, safe for GIS to hold across renders.
  const handleCredentialResponse = useCallback(
    (response: { credential: string }) => {
      login(response.credential)
    },
    [login],
  )

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) return

    // Bail if another instance or strict-mode double-mount already did this
    // (useRef ensures each mount cycle gets its own check).
    if (initRef.current) return
    initRef.current = true

    function initGis() {
      const google = window.google
      if (!google?.accounts?.id) return
      google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCredentialResponse,
        context: 'signin',
        ux_mode: 'popup',
      })
      google.accounts.id.renderButton(buttonContainerRef.current, {
        theme: 'filled_blue',
        size: 'large',
        shape: 'rectangular',
        text: 'signin_with',
        logo_alignment: 'left',
        width: '280',
      })
    }

    if (window.google?.accounts?.id) {
      initGis()
    } else {
      // Script hasn't resolved yet. Poll at 100ms intervals for up to 30s,
      // then give up (network failure, ad-blocker).
      let attempts = 0
      const MAX_ATTEMPTS = 300
      const timer = setInterval(() => {
        attempts++
        if (window.google?.accounts?.id) {
          clearInterval(timer)
          initGis()
        } else if (attempts >= MAX_ATTEMPTS) {
          clearInterval(timer)
        }
      }, 100)
      return () => clearInterval(timer)
    }
  }, [handleCredentialResponse])

  return (
    <div className="flex h-screen flex-col items-center justify-center bg-background text-foreground">
      <div className="flex max-w-md flex-col items-center gap-6 text-center px-6">
        <h1 className="text-3xl font-bold tracking-tight">Spoilerless</h1>
        <p className="text-sm text-muted-foreground">
          A spoiler-safe graph browser for exploring character and event relationships
          as you watch. Sign in with Google to get started.
        </p>

        {!import.meta.env.VITE_GOOGLE_CLIENT_ID && (
          <p className="text-sm text-destructive">
            Google Sign-In is not configured. Set <code>VITE_GOOGLE_CLIENT_ID</code> in the frontend environment.
          </p>
        )}

        {state.status === 'error' && (
          <p className="text-sm text-destructive">{state.message}</p>
        )}

        <div ref={buttonContainerRef} className="min-h-[40px]" />

        {state.status === 'loading' && (
          <p className="text-sm text-muted-foreground">Signing in…</p>
        )}

        {state.status === 'error' && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              // Reset ref so Retry can re-init if needed.
              initRef.current = false
              window.google?.accounts.id.cancel()

              window.google?.accounts.id.initialize({
                client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
                callback: handleCredentialResponse,
                context: 'signin',
                ux_mode: 'popup',
              })
              initRef.current = true

              window.google?.accounts.id.renderButton(buttonContainerRef.current, {
                theme: 'filled_blue',
                size: 'large',
                shape: 'rectangular',
                text: 'signin_with',
                logo_alignment: 'left',
                width: '280',
              })
            }}
          >
            Retry
          </Button>
        )}
      </div>
    </div>
  )
}
