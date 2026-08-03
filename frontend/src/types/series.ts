// Mirrors backend/app/domain/series.py field-for-field.

export type SeriesResponse = {
  id: string
  title: string
  slug: string
}

export type EpisodeResponse = {
  id: string
  series_id: string
  season_number: number
  episode_number: number
  episode_order: number
  code: string
  title: string
  visible_from_order: number
  // D-21 additive display fields (07-03): the backend always returns the
  // already-masked value in `display_title` when a boundary is applied; the
  // legacy `title` field keeps the raw title for backward compatibility.
  display_title?: string | null
  is_unlocked?: boolean | null
  is_current_view?: boolean | null
}
