// Hand-written GraphResponse fixture mirroring the live S01E01 shape
// documented in 02-RESEARCH.md `## Code Examples`:
//   nodes: 11 (Character:6, Event:1, Location:2, Episode:1, Series:1)
//   edges: 6 (types: OCCURRED_IN, PART_OF, WORKS_WITH, FAMILY_OF)
//   claims: 4 (one status:"candidate", valid_until_order:1)
//   sources: 1, evidence: 3

import type { GraphResponse } from '../../types/graph'

export const graphResponseS01E01: GraphResponse = {
  series: { id: 'series_dexter', title: 'Dexter', slug: 'dexter' },
  visible_until_order: 1,
  nodes: [
    { id: 'series_dexter', type: 'Series', label: 'Dexter', visible_from_order: 1, origin: 'canonical', episode_id: null },
    { id: 'dexter_s01e01', type: 'Episode', label: 'S01E01 — Dexter', visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
    { id: 'char_dexter_morgan', type: 'Character', label: 'Dexter Morgan', visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
    { id: 'char_debra_morgan', type: 'Character', label: 'Debra Morgan', visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
    { id: 'char_james_doakes', type: 'Character', label: 'James Doakes', visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
    { id: 'char_rita_bennett', type: 'Character', label: 'Rita Bennett', visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
    { id: 'char_angel_batista', type: 'Character', label: 'Angel Batista', visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
    { id: 'char_ice_truck_killer', type: 'Character', label: 'The Ice Truck Killer', visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
    { id: 'event_first_kill', type: 'Event', label: 'Dexter kills Mike Donovan', visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
    { id: 'loc_miami_metro', type: 'Location', label: 'Miami Metro Police Department', visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
    { id: 'loc_dexters_apartment', type: 'Location', label: "Dexter's Apartment", visible_from_order: 1, origin: 'canonical', episode_id: 'dexter_s01e01' },
  ],
  edges: [
    { id: 'edge_1', source: 'dexter_s01e01', target: 'series_dexter', type: 'PART_OF', visible_from_order: 1, origin: 'canonical', claim_id: null },
    { id: 'edge_2', source: 'char_dexter_morgan', target: 'loc_miami_metro', type: 'OCCURRED_IN', visible_from_order: 1, origin: 'canonical', claim_id: 'claim_1' },
    { id: 'edge_3', source: 'char_dexter_morgan', target: 'char_angel_batista', type: 'WORKS_WITH', visible_from_order: 1, origin: 'canonical', claim_id: 'claim_2' },
    { id: 'edge_4', source: 'char_dexter_morgan', target: 'char_debra_morgan', type: 'FAMILY_OF', visible_from_order: 1, origin: 'canonical', claim_id: 'claim_3' },
    { id: 'edge_5', source: 'char_debra_morgan', target: 'loc_miami_metro', type: 'OCCURRED_IN', visible_from_order: 1, origin: 'canonical', claim_id: null },
    { id: 'edge_6', source: 'char_dexter_morgan', target: 'event_first_kill', type: 'OCCURRED_IN', visible_from_order: 1, origin: 'canonical', claim_id: 'claim_4' },
  ],
  claims: [
    {
      id: 'claim_1', label: 'Dexter works at Miami Metro', subject_id: 'char_dexter_morgan', predicate: 'works_at',
      object_id: 'loc_miami_metro', claim_type: 'explicit_fact', status: 'canonical', confidence_level: 'verified',
      relationship_effect: 0.8, visible_from_order: 1, valid_from_order: 1, valid_until_order: null,
      source_id: 'source_1', evidence_ids: ['evidence_1'], origin: 'canonical',
    },
    {
      id: 'claim_2', label: 'Dexter works with Angel Batista', subject_id: 'char_dexter_morgan', predicate: 'works_with',
      object_id: 'char_angel_batista', claim_type: 'observed_event', status: 'corroborated', confidence_level: 'high',
      relationship_effect: 0.6, visible_from_order: 1, valid_from_order: 1, valid_until_order: null,
      source_id: 'source_1', evidence_ids: ['evidence_2'], origin: 'canonical',
    },
    {
      id: 'claim_3', label: "Debra is Dexter's sister", subject_id: 'char_dexter_morgan', predicate: 'family_of',
      object_id: 'char_debra_morgan', claim_type: 'explicit_fact', status: 'canonical', confidence_level: 'verified',
      relationship_effect: 0.9, visible_from_order: 1, valid_from_order: 1, valid_until_order: null,
      source_id: 'source_1', evidence_ids: ['evidence_3'], origin: 'canonical',
    },
    {
      id: 'claim_4', label: 'Dexter may have killed Mike Donovan', subject_id: 'char_dexter_morgan', predicate: 'involved_in',
      object_id: 'event_first_kill', claim_type: 'inferred_state', status: 'candidate', confidence_level: 'medium',
      relationship_effect: 0.4, visible_from_order: 1, valid_from_order: 1, valid_until_order: 1,
      source_id: 'source_1', evidence_ids: ['evidence_1'], origin: 'canonical',
    },
  ],
  sources: [
    {
      id: 'source_1', label: 'S01E01 script', episode_id: 'dexter_s01e01', source_type: 'script',
      locator: 'S01E01 script', retrieved_at: '2026-01-01T00:00:00Z', visible_from_order: 1, origin: 'canonical',
    },
  ],
  evidence: [
    {
      id: 'evidence_1', label: 'Opening kill scene', episode_id: 'dexter_s01e01', source_id: 'source_1',
      text: 'Dexter narrates his ritual before the kill.', locator: '00:03:12', content_hash: 'hash1',
      visible_from_order: 1, origin: 'canonical',
    },
    {
      id: 'evidence_2', label: 'Lab scene', episode_id: 'dexter_s01e01', source_id: 'source_1',
      text: 'Dexter and Angel process evidence together.', locator: '00:12:34', content_hash: 'hash2',
      visible_from_order: 1, origin: 'canonical',
    },
    {
      id: 'evidence_3', label: 'Sibling dinner scene', episode_id: 'dexter_s01e01', source_id: 'source_1',
      text: 'Dexter has dinner with his sister Debra.', locator: '00:22:10', content_hash: 'hash3',
      visible_from_order: 1, origin: 'canonical',
    },
  ],
}
