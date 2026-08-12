import { Eye } from 'lucide-react'
import { CLAIM_ACCENT_COLOR, EVIDENCE_ACCENT_COLOR } from '../detail/DetailPanel'
import type { Citation } from '../../types/chat'

// Two render modes (PROB-09 #81): a full Citation (chat citations, with
// accent + optional "Show in graph") or a lean label chip (ChangeSetCard's
// affected-elements list — previously faked a Citation with
// episode_code=id to reuse this component).
type Props =
  | { label: string; onOpenDetail?: () => void }
  | {
      citation: Citation
      onShowInGraph?: (citation: Citation) => void
      onOpenDetail?: (citation: Citation) => void
    }

// Reuses DetailPanel.tsx's exact CLAIM_ACCENT_COLOR/EVIDENCE_ACCENT_COLOR
// constants (06-UI-SPEC.md "Citation chip accents") — never a second,
// drifting hex literal. A source-only citation (neither claim_id nor
// evidence_id) gets a muted border with no color accent.
export function CitationChip(props: Props) {
  if ('label' in props) {
    return (
      <div className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card py-1 pr-2 pl-2 text-xs">
        <button
          type="button"
          className="font-semibold text-muted-foreground transition-colors hover:text-foreground"
          onClick={() => props.onOpenDetail?.()}
        >
          {props.label}
        </button>
      </div>
    )
  }

  const { citation, onShowInGraph, onOpenDetail } = props
  const hasGraphTargets = citation.related_node_ids.length + citation.related_edge_ids.length > 0
  const accentColor = citation.claim_id
    ? CLAIM_ACCENT_COLOR
    : citation.evidence_id
      ? EVIDENCE_ACCENT_COLOR
      : null

  return (
    <div
      className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card py-1 pr-2 pl-2 text-xs"
      style={accentColor ? { borderLeft: `4px solid ${accentColor}` } : undefined}
    >
      <button
        type="button"
        className="font-semibold text-muted-foreground transition-colors hover:text-foreground"
        onClick={() => onOpenDetail?.(citation)}
      >
        {citation.source_type} · {citation.episode_code}
      </button>
      {hasGraphTargets && (
        <button
          type="button"
          aria-label="Show in graph"
          className="min-h-[44px] text-secondary transition-colors hover:text-secondary/80"
          onClick={() => onShowInGraph?.(citation)}
        >
          <Eye className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
