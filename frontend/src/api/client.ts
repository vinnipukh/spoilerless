// Shared fetch client mirroring backend/app/core/errors.py's
// `{detail: {code, message}}` error envelope (404 series_not_found, 422
// invalid_visible_until_order, 503 database_unavailable/database_error).

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

export async function apiFetch<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(body?.detail ?? { code: 'unknown_error', message: 'Request failed.' })
  }
  return res.json() as Promise<T>
}
