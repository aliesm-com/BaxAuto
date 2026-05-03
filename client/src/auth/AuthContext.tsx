import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import * as authApi from '@/api/auth'
import type { ImpersonatorInfo } from '@/api/auth'
import { clearTokens, getAccessToken } from '@/api/client'
import type { AuthUser } from '@/types/user'

interface AuthState {
  user: AuthUser | null
  loading: boolean
  impersonator: ImpersonatorInfo | null
  login: (username: string, password: string) => Promise<void>
  loginAs: (userId: number) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [impersonator, setImpersonator] = useState<ImpersonatorInfo | null>(() => authApi.readImpersonator())
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null)
      setImpersonator(null)
      setLoading(false)
      return
    }
    try {
      const me = await authApi.fetchMe()
      setUser(me)
      setImpersonator(authApi.readImpersonator())
    } catch {
      clearTokens()
      setUser(null)
      setImpersonator(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshUser()
  }, [refreshUser])

  const login = useCallback(async (username: string, password: string) => {
    const data = await authApi.login(username, password)
    setUser(data.user)
    setImpersonator(null)
  }, [])

  const loginAs = useCallback(async (userId: number) => {
    const data = await authApi.loginAs(userId)
    setUser(data.user)
    setImpersonator(authApi.readImpersonator())
  }, [])

  const logout = useCallback(async () => {
    await authApi.logout()
    setUser(null)
    setImpersonator(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      impersonator,
      login,
      loginAs,
      logout,
      refreshUser,
    }),
    [user, loading, impersonator, login, loginAs, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
