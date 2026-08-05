import { createContext } from 'react'
import type { User } from '../types/auth'

export type AuthState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'visitor' }
  | { status: 'authenticated'; user: User }
  | { status: 'error'; message: string }

export type AuthContextValue = {
  state: AuthState
  login: (credential: string) => Promise<void>
  logout: () => Promise<void>
  // Quick task 260805-te3: read-only "misafir" (visitor) mode — browse the
  // graph without an account. Backend already 401s every anonymous write,
  // so this is purely a frontend entry/gate concern.
  enterVisitor: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
