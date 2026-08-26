import { useCallback, useState } from 'react'

// 12-08 (THERMO-P0-02): top-level view + tab navigation state extracted from
// App.tsx. Owns the graph/timeline/settings view switch, the four-tab
// narrative hierarchy with its per-tab nested modes, and the command palette
// open state. Mode setters are returned as stable callbacks so App handlers
// compose them without prop-drilling raw setState.
type StoryTab = 'story' | 'characters' | 'evidence' | 'advanced'
type StoryMode = 'episode_overview' | 'event_timeline'
type CharacterMode = 'character_network' | 'local_neighborhood'
type EvidenceMode = 'investigation' | 'evidence_chain' | 'answer_graph'
type AdvancedMode = 'full_graph' | 'debug'

export type WorkspaceView = 'graph' | 'timeline' | 'settings'

export function useWorkspaceNavigation() {
  // Top-level view switch: the graph workspace, the timeline, or the
  // settings page (no router in this app — navigation is state-driven).
  const [view, setView] = useState<WorkspaceView>('graph')
  const [topTab, setTopTab] = useState<StoryTab>('story')
  const [storyMode, setStoryMode] = useState<StoryMode>('episode_overview')
  const [characterMode, setCharacterMode] = useState<CharacterMode>('character_network')
  const [evidenceMode, setEvidenceMode] = useState<EvidenceMode>('investigation')
  const [advancedMode, setAdvancedMode] = useState<AdvancedMode>('full_graph')
  const [paletteOpen, setPaletteOpen] = useState(false)

  const openTimeline = useCallback(() => setView('timeline'), [])
  const openSettings = useCallback(() => setView('settings'), [])
  const closeToGraph = useCallback(() => setView('graph'), [])

  return {
    view,
    setView,
    openTimeline,
    openSettings,
    closeToGraph,
    topTab,
    setTopTab,
    storyMode,
    setStoryMode,
    characterMode,
    setCharacterMode,
    evidenceMode,
    setEvidenceMode,
    advancedMode,
    setAdvancedMode,
    paletteOpen,
    setPaletteOpen,
  }
}
