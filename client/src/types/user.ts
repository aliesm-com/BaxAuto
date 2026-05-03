export interface AuthUser {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  is_superuser: boolean
  is_viewer: boolean
  is_editor: boolean
  is_admin: boolean
  phone_number: string | null
  country_code: string | null
}

export interface LoginResponse {
  access: string
  refresh: string
  user: AuthUser
}

/** Superuser-only login-as response (same tokens shape as login). */
export interface LoginAsResponse extends LoginResponse {
  impersonator_id: number
  impersonator_username: string
}
