import { useState } from 'react'
import { apiUrl } from '../../api/client'
import type { GraphNode } from '../../types/graph'

function initialsFor(label: string): string {
  const initials = label
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
  return initials || '?'
}

// Portrait shown next to a Character's name in the detail panel header.
// Falls back to an initials avatar both when image_url is null AND when the
// external image fails to load (broken link, 404, blocked) — never renders
// an empty broken-image box.
//
// D-14/MEDIA-02: the two fallback paths (missing vs failed) render the
// IDENTICAL placeholder (same testid, same classes, no error text, no retry
// affordance) so a failed image request can never imply a hidden future
// character exists. The alt text is always the safe visible label, never a
// filename or URL.
//
// 12-08 (THERMO-P0-04): extracted verbatim from DetailPanel.tsx.
export function CharacterPortrait({
  node,
  visibleUntilOrder,
}: {
  node: GraphNode
  visibleUntilOrder: number | null
}) {
  const [failed, setFailed] = useState(false)
  const showImage = Boolean(node?.image_url) && !failed

  // D-14 defensive guard: the image source link renders only when the
  // resource is visible at the current boundary. The backend already nulls
  // image_source_url above the boundary; this makes a future regression
  // unable to surface a URL as text. A null/unknown boundary fails closed —
  // no link.
  const isVisibleAtBoundary =
    visibleUntilOrder != null && node.visible_from_order <= visibleUntilOrder
  const showSourceLink = Boolean(node.image_source_url) && isVisibleAtBoundary

  const avatar = showImage ? (
    <img
      src={apiUrl(node.image_url) ?? undefined}
      alt={node.label}
      className="h-10 w-10 rounded-full object-cover"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      loading="lazy"
    />
  ) : (
    <div
      data-testid="character-avatar"
      className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground"
    >
      {initialsFor(node.label)}
    </div>
  )

  if (!showSourceLink) return avatar

  // Generic accessible link label — never the URL (D-14: URLs and filenames
  // never appear as user-visible text).
  return (
    <a
      href={node.image_source_url ?? undefined}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Image source"
    >
      {avatar}
    </a>
  )
}
