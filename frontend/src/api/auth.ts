import { apiFetch } from './client'
import type { GoogleAuthRequest, UserResponse } from '../types/auth'

export function loginWithGoogleCredential(credential: string): Promise<UserResponse> {
  return apiFetch<UserResponse>('/api/auth/google', {
    method: 'POST',
    body: { credential } satisfies GoogleAuthRequest,
  })
}

export function getCurrentUser(): Promise<UserResponse> {
  return apiFetch<UserResponse>('/api/auth/me')
}

export function logout(): Promise<void> {
  return apiFetch<void>('/api/auth/logout', { method: 'POST' })
}
