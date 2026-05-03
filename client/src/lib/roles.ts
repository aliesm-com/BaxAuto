import type { AuthUser } from '@/types/user'

export function roleLabel(user: AuthUser): string {
  if (user.is_superuser || user.is_admin) return 'Admin'
  if (user.is_editor) return 'Editor'
  if (user.is_viewer) return 'Viewer'
  return 'User'
}

export function displayName(user: AuthUser): string {
  const n = [user.first_name, user.last_name].filter(Boolean).join(' ')
  return n || user.username
}
