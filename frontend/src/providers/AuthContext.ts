import { createContext } from 'react'
import type { User } from '../types/auth'

export type AuthState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'authenticated'; user: User }
  | { status: 'error'; message: string }

export type AuthContextValue = {
  state: AuthState
  login: (credential: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
