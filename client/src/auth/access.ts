import type { AuthUser } from '@/types/user'

/** Read-only app role: viewer without editor/admin/superuser. Plain users (no flags) can still mutate. */
export function isViewerOnly(user: AuthUser | null | undefined): boolean {
  if (!user) return false
  if (user.is_superuser || user.is_admin || user.is_editor) return false
  return user.is_viewer
}

export function canMutate(user: AuthUser | null | undefined): boolean {
  if (!user) return false
  return !isViewerOnly(user)
}

export function canManageSchedules(user: AuthUser | null | undefined): boolean {
  return Boolean(user?.is_superuser || user?.is_admin)
}

export function canManageUsers(user: AuthUser | null | undefined): boolean {
  return Boolean(user?.is_superuser || user?.is_admin)
}

export function canLoginAs(user: AuthUser | null | undefined): boolean {
  return Boolean(user?.is_superuser)
}
