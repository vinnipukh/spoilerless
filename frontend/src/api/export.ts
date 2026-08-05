import { ApiError } from './client'

const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''

export async function fetchExportMarkdown(
  seriesId: string,
  visibleUntilOrder: number = 1,
  targetId?: string,
): Promise<{ text: string; filename: string }> {
  const query = new URLSearchParams({ visible_until_order: String(visibleUntilOrder) })
  if (targetId) query.set('target_id', targetId)

  const res = await fetch(`${apiBase}/api/series/${seriesId}/export?${query.toString()}`, {
    method: 'GET',
    credentials: 'include',
  })

  if (!res.ok) {
    const responseBody = await res.json().catch(() => null)
    throw new ApiError(responseBody?.detail ?? { code: 'UNKNOWN_ERROR', message: 'Export request failed.' })
  }

  const text = await res.text()
  const contentDisposition = res.headers.get('Content-Disposition')
  let filename = `spoilerless-${seriesId}.md`
  if (contentDisposition) {
    const match = /filename="?([^";]+)"?/.exec(contentDisposition)
    if (match?.[1]) filename = match[1]
  }

  return { text, filename }
}

export function downloadMarkdownBlob(text: string, filename: string): void {
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
