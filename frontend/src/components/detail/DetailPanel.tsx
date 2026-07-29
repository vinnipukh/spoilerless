import { useEffect, useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import type { SelectedElement } from '../graph/GraphCanvas'
import type { GraphClaim, GraphEvidence, GraphNode, GraphResponse } from '../../types/graph'

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
function CharacterPortrait({ node }: { node: GraphNode }) {
  const [failed, setFailed] = useState(false)
  const showImage = Boolean(node.image_url) && !failed

  const avatar = showImage ? (
    <img
      src={node.image_url ?? undefined}
      alt={node.label}
      className="h-10 w-10 rounded-full object-cover"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
    />
  ) : (
    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground">
      {initialsFor(node.label)}
    </div>
  )

  if (!node.image_source_url) return avatar

  return (
    <a
      href={node.image_source_url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Open ${node.label} on Fandom`}
    >
      {avatar}
    </a>
  )
}

// Full Overview/Claims/Evidence tabbed Sheet (D-07) for nodes and claim-backed
// narrative edges (edge.claim_id !== null). Structural edges (claim_id ===
// null) never reach this component — App.tsx routes those to
// StructuralEdgeCard instead (D-06), so every branch below can assume the
// selected edge (if any) is claim-backed.
type Props = {
  selected: SelectedElement | null
  graph: GraphResponse
}

type ResolvedEvidence = {
  evidence: GraphEvidence
  sourceLabel: string
}

function resolveClaimsForSelection(
  selected: SelectedElement | null,
  graph: GraphResponse,
): GraphClaim[] {
  if (!selected) return []

  if (selected.kind === 'node') {
    return graph.claims.filter(
      (claim) => claim.subject_id === selected.id || claim.object_id === selected.id,
    )
  }

  // Edge selection: DetailPanel only ever renders for claim-backed edges
  // (App.tsx's centralized branch keeps structural edges out of this
  // component entirely) — resolve the single associated claim via the full
  // GraphResponse rather than widening GraphCanvas's onSelect contract.
  const graphEdge = graph.edges.find((edge) => edge.id === selected.id)
  const claim = graphEdge?.claim_id
    ? graph.claims.find((c) => c.id === graphEdge.claim_id)
    : undefined
  return claim ? [claim] : []
}

function resolveEvidenceForClaims(claims: GraphClaim[], graph: GraphResponse): ResolvedEvidence[] {
  const seen = new Set<string>()
  const resolved: ResolvedEvidence[] = []

  for (const claim of claims) {
    for (const evidenceId of claim.evidence_ids) {
      if (seen.has(evidenceId)) continue
      const evidence = graph.evidence.find((entry) => entry.id === evidenceId)
      if (!evidence) continue
      seen.add(evidenceId)
      const source = graph.sources.find((entry) => entry.id === evidence.source_id)
      resolved.push({ evidence, sourceLabel: source?.label ?? evidence.source_id })
    }
  }

  return resolved
}

export function DetailPanel({ selected, graph }: Props) {
  // Claims/Evidence content is a synchronous lookup over the already-fetched
  // GraphResponse (no network round trip) — a one-tick Skeleton gates the
  // Claims/Evidence tab bodies while this local resolve "runs" (UI-SPEC UI
  // Considerations — loading/detail panel on node click, backstop).
  //
  // Resetting `resolved` to false when the selection changes happens here,
  // during render, comparing against a *state* copy of the previous
  // selection key — the same "adjusting state when a prop changes" pattern
  // used by useGraph.ts's key-comparison reset — so the effect below only
  // ever flips `resolved` back to true from an async callback, never a bare
  // synchronous setState in the effect body (react-hooks/set-state-in-effect).
  const selectionKey = selected ? `${selected.kind}:${selected.id}` : 'none'
  const [resolved, setResolved] = useState(false)
  const [prevSelectionKey, setPrevSelectionKey] = useState(selectionKey)
  if (prevSelectionKey !== selectionKey) {
    setPrevSelectionKey(selectionKey)
    setResolved(false)
  }

  useEffect(() => {
    if (resolved) return
    const id = setTimeout(() => setResolved(true), 0)
    return () => clearTimeout(id)
  }, [resolved])

  const selectedNode =
    selected?.kind === 'node' ? graph.nodes.find((node) => node.id === selected.id) : undefined
  const relevantClaims = resolveClaimsForSelection(selected, graph)
  const activeClaim = selected?.kind === 'edge' ? relevantClaims[0] : undefined
  const evidenceEntries = resolveEvidenceForClaims(relevantClaims, graph)

  const title = selectedNode?.label ?? activeClaim?.label ?? 'Details'

  return (
    <Sheet open modal={false}>
      <SheetContent side="right" showCloseButton={false} className="mt-0">
        <SheetHeader>
          <div className="flex items-center gap-3">
            {selectedNode?.type === 'Character' && (
              <CharacterPortrait key={selectedNode.id} node={selectedNode} />
            )}
            <SheetTitle>{selected ? title : 'Details'}</SheetTitle>
          </div>
        </SheetHeader>
        <div className="flex flex-col gap-2 px-4 pb-4 text-sm">
          {!selected && <p>Select a node to see details.</p>}
          {selected && (
            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="claims">Claims</TabsTrigger>
                <TabsTrigger value="evidence">Evidence</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="flex flex-col gap-1 pt-2">
                {selected.kind === 'node' && selectedNode && (
                  <>
                    <p>Type: {selectedNode.type}</p>
                    <p>Label: {selectedNode.label}</p>
                  </>
                )}
                {selected.kind === 'edge' && activeClaim && (
                  <>
                    <p>Predicate: {activeClaim.predicate}</p>
                    <p>Claim type: {activeClaim.claim_type}</p>
                    <p>Status: {activeClaim.status}</p>
                    <p>Confidence: {activeClaim.confidence_level}</p>
                  </>
                )}
              </TabsContent>

              <TabsContent value="claims" className="flex flex-col gap-2 pt-2">
                {!resolved && <Skeleton className="h-16 w-full" />}
                {resolved && relevantClaims.length === 0 && (
                  <p>No claims recorded for this node yet</p>
                )}
                {resolved &&
                  relevantClaims.map((claim) => (
                    <div key={claim.id} className="rounded-md border border-border p-2">
                      <p className="font-medium">{claim.label}</p>
                      <p className="text-muted-foreground">
                        {claim.predicate} · {claim.status} · {claim.confidence_level}
                      </p>
                    </div>
                  ))}
              </TabsContent>

              <TabsContent value="evidence" className="flex flex-col gap-2 pt-2">
                {!resolved && <Skeleton className="h-16 w-full" />}
                {resolved && evidenceEntries.length === 0 && (
                  <p>No evidence recorded for this claim yet</p>
                )}
                {resolved &&
                  evidenceEntries.map(({ evidence, sourceLabel }) => (
                    <div
                      key={evidence.id}
                      className="max-h-32 overflow-y-auto rounded-md border border-border p-2"
                    >
                      <p>
                        Source: {sourceLabel} - {evidence.locator}
                      </p>
                      <p className="text-muted-foreground">{evidence.text}</p>
                    </div>
                  ))}
              </TabsContent>
            </Tabs>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
