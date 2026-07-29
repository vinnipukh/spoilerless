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
}
