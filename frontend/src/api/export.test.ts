import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchExportMarkdown, downloadMarkdownBlob } from './export'
import { renderGraphMarkdown, exportFilename } from '../lib/exportMarkdown'
import type { GraphResponse } from '../types/graph'

const dummyGraph: GraphResponse = {
  series: {
    id: 'series_dexter',
    title: 'Dexter',
    slug: 'dexter',
  },
  visible_until_order: 1,
  nodes: [
    {
      id: 'node1',
      type: 'Character',
      label: 'Dexter Morgan',
      visible_from_order: 1,
      origin: 'canonical',
      episode_id: null,
      image_url: null,
      image_source_url: null,
    },
    {
      id: 'ep1',
      type: 'Episode',
      label: 'S01E01',
      visible_from_order: 1,
      origin: 'canonical',
      episode_id: null,
      image_url: null,
      image_source_url: null,
    },
  ],
  edges: [],
  claims: [
    {
      id: 'claim1',
      label: 'Temporary trust',
      subject_id: 'node1',
      predicate: 'TRUSTS',
      object_id: 'node1',
      claim_type: 'explicit_fact',
      status: 'active',
      confidence_level: 'high',
      relationship_effect: 1,
      visible_from_order: 1,
      valid_from_order: null,
      valid_until_order: null,
      source_id: 'source1',
      evidence_ids: ['evidence1'],
      origin: 'canonical',
    },
  ],
  sources: [
    {
      id: 'source1',
      label: 'S01E01 transcript',
      episode_id: 'ep1',
      source_type: 'transcript',
      locator: '00:10:00',
      retrieved_at: '2026-01-01',
      visible_from_order: 1,
      origin: 'canonical',
    },
  ],
  evidence: [
    {
      id: 'evidence1',
      label: 'Dexter says he trusts Debra',
      episode_id: 'ep1',
      source_id: 'source1',
      text: 'I trust my sister',
      locator: '00:10:00',
      content_hash: 'hash1',
      visible_from_order: 1,
      origin: 'canonical',
    },
  ],
}

describe('export API and library helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchExportMarkdown builds the correct URL and parses Content-Disposition filename', async () => {
    const mockResponseText = '# Dexter\n\n## Episodes\n- S01E01'
    const globalFetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(mockResponseText),
      headers: {
        get: (header: string) =>
          header.toLowerCase() === 'content-disposition'
            ? 'attachment; filename="spoilerless-dexter-order-1.md"'
            : null,
      },
    })
    vi.stubGlobal('fetch', globalFetch)

    const result = await fetchExportMarkdown('series_dexter', 1)

    expect(globalFetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/export?visible_until_order=1',
      expect.objectContaining({
        method: 'GET',
        credentials: 'include',
      }),
    )
    expect(result.text).toBe(mockResponseText)
    expect(result.filename).toBe('spoilerless-dexter-order-1.md')

    vi.unstubAllGlobals()
  })

  it('fetchExportMarkdown passes target_id query param when targetId is provided', async () => {
    const globalFetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve('# Dexter Morgan'),
      headers: {
        get: () => null,
      },
    })
    vi.stubGlobal('fetch', globalFetch)

    await fetchExportMarkdown('series_dexter', 1, 'node1')

    expect(globalFetch).toHaveBeenCalledWith(
      '/api/series/series_dexter/export?visible_until_order=1&target_id=node1',
      expect.anything(),
    )

    vi.unstubAllGlobals()
  })

  it('renderGraphMarkdown correctly formats whole graph and node target markdown', () => {
    const wholeGraphMd = renderGraphMarkdown(dummyGraph)
    expect(wholeGraphMd).toContain('# Dexter')
    expect(wholeGraphMd).toContain('## Episodes')
    expect(wholeGraphMd).toContain('S01E01')
    expect(wholeGraphMd).toContain('## Characters')
    expect(wholeGraphMd).toContain('Dexter Morgan')

    const nodeTargetMd = renderGraphMarkdown(dummyGraph, 'node1')
    expect(nodeTargetMd).toContain('# Dexter')
    expect(nodeTargetMd).toContain('## Dexter Morgan')
    expect(nodeTargetMd).toContain('- Type: `Character`')
    expect(nodeTargetMd).toContain('### Claims')
    expect(nodeTargetMd).toContain('Temporary trust')
    expect(nodeTargetMd).toContain('Evidence: Dexter says he trusts Debra')
  })

  it('exportFilename generates expected filenames', () => {
    expect(exportFilename(dummyGraph)).toBe('spoilerless-dexter-order-1.md')
    expect(exportFilename(dummyGraph, 'node1')).toBe('spoilerless-dexter-morgan.md')
  })

  it('downloadMarkdownBlob creates a Blob with text/markdown type and triggers download', () => {
    const createObjectURL = vi.fn().mockReturnValue('blob:http://localhost/1234')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })

    const clickMock = vi.fn()
    const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: clickMock,
    } as unknown as HTMLAnchorElement)
    const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => ({} as unknown as HTMLElement))
    const removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation(() => ({} as unknown as HTMLElement))

    downloadMarkdownBlob('# Test', 'test.md')

    expect(createObjectURL).toHaveBeenCalled()
    expect(clickMock).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/1234')

    createElementSpy.mockRestore()
    appendChildSpy.mockRestore()
    removeChildSpy.mockRestore()
    vi.unstubAllGlobals()
  })
})
