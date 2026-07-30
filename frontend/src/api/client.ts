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

  constructor(detail: ApiErrorDetail) {
    super(detail.message)
    this.name = 'ApiError'
    this.code = detail.code
  }
}

type FetchOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
}

export async function apiFetch<T>(url: string, options?: FetchOptions): Promise<T> {
  const { method = 'GET', body, headers } = options ?? {}
  const res = await fetch(url, {
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
