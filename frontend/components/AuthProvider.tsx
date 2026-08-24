'use client'

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getMe } from '@/lib/api'
import type { UserResponse } from '@/lib/types'

interface AuthContextValue {
  user: UserResponse | null
  isLoading: boolean
  signIn: (token: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  signIn: async () => {},
  signOut: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => localStorage.removeItem('token'))
        .finally(() => setIsLoading(false))
    } else {
      Promise.resolve().then(() => setIsLoading(false))
    }
  }, [])

  const signIn = useCallback(async (token: string) => {
    localStorage.setItem('token', token)
    const me = await getMe()
    setUser(me)
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem('token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
