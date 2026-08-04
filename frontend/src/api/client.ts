// Shared fetch client mirroring backend/app/core/errors.py's
// `{detail: {code, message}}` error envelope (404 series_not_found, 422
// invalid_visible_until_order, 503 database_unavailable/database_error).
//
// All requests use `credentials: "include"` so the HttpOnly session cookie
// is sent with every request.

export type ApiErrorDetail = {
  code: string
  message: string
}

export class ApiError extends Error {
  code: string

  constructor(detail: ApiErrorDetail | Array<{ msg?: string }>) {
    // FastAPI validation errors carry `detail` as an array of {loc, msg,
    // type} entries rather than the app's {code, message} envelope —
    // normalize both shapes so a 422 always surfaces a real message.
    super(Array.isArray(detail) ? (detail[0]?.msg ?? 'Request failed.') : detail.message)
    this.name = 'ApiError'
    this.code = Array.isArray(detail) ? 'invalid_request' : detail.code
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

export async function apiFetch<T>(url: string, options?: FetchOptions): Promise<T> {
  const { method = 'GET', body, headers } = options ?? {}
  const res = await fetch(`${apiBase}${url}`, {
    method,
    headers: {
      'Content-Type': body !== undefined ? 'application/json' : '',
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
    throw new ApiError(responseBody?.detail ?? { code: 'unknown_error', message: 'Request failed.' })
  }

  return res.json() as Promise<T>
}
