import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { AppUser } from '../types'
import { api } from '../services/api'

interface AuthContextValue {
  user: AppUser | null
  loading: boolean
  login: (username: string, password: string) => Promise<AppUser>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      setLoading(false)
      return
    }
    api.getCurrentUser()
      .then(setUser)
      .catch(() => {
        api.logout()
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    async login(username, password) {
      const response = await api.login(username, password)
      setUser(response.user)
      return response.user
    },
    logout() {
      api.logout()
      setUser(null)
    },
  }), [user, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return context
}
