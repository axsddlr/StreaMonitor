import { useState, useCallback } from 'react'
import { getToken, setToken, login as apiLogin } from '@/api/client'

export interface UseAuthReturn {
  token: string | null
  isAuthenticated: boolean
  login: (password: string) => Promise<void>
  logout: () => void
}

export function useAuth(): UseAuthReturn {
  const [token, setTokenState] = useState<string | null>(() => getToken())

  const login = useCallback(async (password: string): Promise<void> => {
    const response = await apiLogin(password)
    setToken(response.token)
    setTokenState(response.token)
  }, [])

  const logout = useCallback((): void => {
    setToken(null)
    setTokenState(null)
  }, [])

  return {
    token,
    isAuthenticated: token !== null,
    login,
    logout,
  }
}
