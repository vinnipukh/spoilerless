export type ShareTokenCreateRequest = {
  series_id: string
  visible_until_order: number
}

export type ShareTokenCreateResponse = {
  token: string
  expires_at: number
  url: string
  series_id: string
  visible_until_order: number
  created_at: number
}

export type ShareTokenItem = {
  id: string
  token_hash: string
  series_id: string
  visible_until_order: number
  created_at: number
  expires_at: number
}
