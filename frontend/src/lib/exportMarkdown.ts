import type { GraphResponse } from '@/types/graph'

function slugify(val: string): string {
  const slug = val.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  return slug || 'export'
}

export function exportFilename(graph: GraphResponse, targetId?: string): string {
  if (targetId) {
    const node = graph.nodes.find((n) => n.id === targetId)
    const label = node ? slugify(node.label) : 'node'
    return `spoilerless-${label}.md`
  }
  const slug = slugify(graph.series.slug)
  return `spoilerless-${slug}-order-${graph.visible_until_order}.md`
}

export function renderGraphMarkdown(graph: GraphResponse, targetId?: string): string {
  const lines: string[] = [`# ${graph.series.title}`, '']

  if (targetId) {
    const node = graph.nodes.find((n) => n.id === targetId)
    if (!node) {
      return `${lines[0]}\n\n_Requested resource is not visible at the current boundary._\n`
    }
    lines.push(`## ${node.label}`, '')
    lines.push(`- Type: \`${node.type}\``)
    lines.push(`- Visible from order: ${node.visible_from_order}`, '')
    appendClaimsFor(lines, graph, targetId)
    return lines.join('\n').trimEnd() + '\n'
  }

  const episodes = graph.nodes.filter((n) => n.type === 'Episode')
  if (episodes.length > 0) {
    lines.push('## Episodes', '')
    for (const ep of episodes) {
      lines.push(`- ${ep.label}`)
    }
    lines.push('')
  }

  const characters = graph.nodes.filter((n) => n.type === 'Character')
  if (characters.length > 0) {
    lines.push('## Characters', '')
    for (const c of characters) {
      lines.push(`- ${c.label}`)
    }
    lines.push('')
  }

  if (graph.claims.length > 0) {
    lines.push('## Claims', '')
    for (const claim of graph.claims) {
      lines.push(`- **${claim.label}** (${claim.predicate})`)
      appendEvidenceFor(lines, graph, claim)
    }
    lines.push('')
  }

  return lines.join('\n').trimEnd() + '\n'
}

function appendClaimsFor(lines: string[], graph: GraphResponse, nodeId: string): void {
  const claims = graph.claims.filter((c) => c.subject_id === nodeId || c.object_id === nodeId)
  if (claims.length === 0) {
    lines.push('_No visible claims for this resource._', '')
    return
  }
  lines.push('### Claims', '')
  for (const claim of claims) {
    lines.push(`- **${claim.label}** (${claim.predicate}, ${claim.confidence_level})`)
    appendEvidenceFor(lines, graph, claim)
  }
  lines.push('')
}

function appendEvidenceFor(lines: string[], graph: GraphResponse, claim: GraphResponse['claims'][number]): void {
  const evidenceById = new Map(graph.evidence.map((e) => [e.id, e]))
  const sourcesById = new Map(graph.sources.map((s) => [s.id, s]))

  for (const evId of claim.evidence_ids) {
    const ev = evidenceById.get(evId)
    if (!ev) continue
    lines.push(`  - Evidence: ${ev.label}`)
    const source = sourcesById.get(ev.source_id)
    if (source && source.locator) {
      lines.push(`    - Source: ${source.label} — ${source.locator}`)
    }
  }
}
