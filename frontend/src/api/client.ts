// Shared fetch client mirroring spoilerless/app/core/errors.py's
// `{detail: {code, message}}` error envelope (404 RESOURCE_NOT_FOUND, 422
// INVALID_REQUEST, 503 DATABASE_UNAVAILABLE/DATABASE_ERROR).
//
// All requests use `credentials: "include"` so the HttpOnly session cookie
// is sent with every request.

export type ApiErrorDetail = {
  code: string
  message: string
}

// FastAPI validation-error entries (422 detail arrays): `loc`/`msg`/`type`.
export type ApiValidationErrorItem = {
  loc?: (string | number)[]
  msg?: string
  type?: string
}

export class ApiError extends Error {
  code: string

  constructor(detail: ApiErrorDetail | ApiValidationErrorItem[]) {
    // FastAPI validation errors carry `detail` as an array of {loc, msg,
    // type} entries rather than the app's {code, message} envelope —
    // normalize both shapes so a 422 always surfaces a real message.
    // The synthesized code matches the backend's canonical uppercase
    // convention (PROB-09/#20) — INVALID_REQUEST is what the shared
    // validation handler emits on the wire.
    super(Array.isArray(detail) ? (detail[0]?.msg ?? 'Request failed.') : detail.message)
    this.name = 'ApiError'
    this.code = Array.isArray(detail) ? 'INVALID_REQUEST' : detail.code
  }
}

type FetchOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
}

// VITE_API_BASE_URL prefixes every apiFetch request in production (direct
// cross-origin call to the hosted backend, e.g. https://api.spoilerless.net);
// '' when unset preserves the relative-URL local-dev behavior through the
// Vite proxy.
const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''

// Backend-relative URLs that bypass apiFetch (Character portrait image_url
// values, served as '/api/static/...') need the same production prefixing.
// Reads VITE_API_BASE_URL at CALL time (not module scope) so tests can
// vi.stubEnv it after import. Only '/'-leading paths are prefixed: absolute
// http(s) URLs and bare relative segments pass through unchanged, and an
// empty base (local dev, '' ) keeps the Vite-proxy behavior.
export function apiUrl(path: string | null): string | null {
  if (path == null) return null
  if (!path.startsWith('/')) return path
  return `${import.meta.env.VITE_API_BASE_URL ?? ''}${path}`
}

export async function apiFetch<T>(url: string, options?: FetchOptions): Promise<T> {
  const { method = 'GET', body, headers } = options ?? {}
  const res = await fetch(`${apiBase}${url}`, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })

  // 204 No Content
  if (res.status === 204) {
    return undefined as T
  }

  if (!res.ok) {
    const responseBody = await res.json().catch(() => null)
    throw new ApiError(responseBody?.detail ?? { code: 'UNKNOWN_ERROR', message: 'Request failed.' })
  }

  return res.json() as Promise<T>
}
