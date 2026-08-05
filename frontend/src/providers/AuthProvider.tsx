import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { loginWithGoogleCredential, getCurrentUser, logout as logoutApi } from '../api/auth'
import { ApiError } from '../api/client'
import { AuthContext, type AuthState } from './AuthContext'

// Quick task 260805-te3: visitor (misafir) read-only mode is remembered per
// browser session so a reload does not kick a visitor back to the login wall.
// A real Google session always wins over the flag (/me 200 → authenticated).
const VISITOR_STORAGE_KEY = 'spoilerless.visitor'

function readVisitorFlag(): boolean {
  try {
    return sessionStorage.getItem(VISITOR_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading' })

  // On mount, try to restore session via GET /api/auth/me
  useEffect(() => {
    let cancelled = false
    getCurrentUser()
      .then((res) => {
        if (!cancelled) setState({ status: 'authenticated', user: res.user })
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.code === 'AUTH_UNAUTHENTICATED') {
          // No session: honor a previously-chosen visitor mode for this tab.
          setState(readVisitorFlag() ? { status: 'visitor' } : { status: 'unauthenticated' })
        } else {
          setState({ status: 'unauthenticated' })
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (credential: string) => {
    setState({ status: 'loading' })
    try {
      const res = await loginWithGoogleCredential(credential)
      try {
        sessionStorage.removeItem(VISITOR_STORAGE_KEY)
      } catch {
        // storage unavailable — non-fatal
      }
      setState({ status: 'authenticated', user: res.user })
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Network error. Please try again.'
      setState({ status: 'error', message })
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutApi()
    } catch {
      // Even if the logout API call fails, clear local state
    }
    try {
      sessionStorage.removeItem(VISITOR_STORAGE_KEY)
    } catch {
      // storage unavailable — non-fatal
    }
    setState({ status: 'unauthenticated' })
  }, [])

  const enterVisitor = useCallback(() => {
    try {
      sessionStorage.setItem(VISITOR_STORAGE_KEY, '1')
    } catch {
      // storage unavailable — non-fatal; visitor mode still applies in-memory
    }
    setState({ status: 'visitor' })
  }, [])

  return (
    <AuthContext.Provider value={{ state, login, logout, enterVisitor }}>
      {children}
    </AuthContext.Provider>
  )
}
