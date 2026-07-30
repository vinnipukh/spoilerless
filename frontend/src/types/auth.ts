// Mirrors backend/app/domain/auth.py field-for-field.
// google_sub is intentionally excluded from the public response model.

export type User = {
  id: string
  email: string
  display_name: string
  avatar_url: string
  created_at: string
  updated_at: string
}

export type UserResponse = {
  user: User
}

export type GoogleAuthRequest = {
  credential: string
}
