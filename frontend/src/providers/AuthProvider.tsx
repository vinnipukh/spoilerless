import { useEffect, useState, useCallback, type ReactNode } from 'react'
import { loginWithGoogleCredential, getCurrentUser, logout as logoutApi } from '../api/auth'
import { ApiError } from '../api/client'
import { AuthContext, type AuthState } from './AuthContext'

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
          setState({ status: 'unauthenticated' })
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
    setState({ status: 'unauthenticated' })
  }, [])

  return (
    <AuthContext.Provider value={{ state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
