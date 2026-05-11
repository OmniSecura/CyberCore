import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api/client'

const REFRESH_MS = 10 * 60 * 1000 // 10 minutes

export function useAuth() {
  const [user,   setUser]   = useState(null)
  // 'loading' | 'authenticated' | 'unauthenticated'
  const [status, setStatus] = useState('loading')
  const timer               = useRef(null)

  const stopRefresh = useCallback(() => {
    clearInterval(timer.current)
    timer.current = null
  }, [])

  const startRefresh = useCallback(() => {
    stopRefresh()
    timer.current = setInterval(async () => {
      try {
        await api('POST', '/users/refresh')
      } catch {
        stopRefresh()
        setUser(null)
        setStatus('unauthenticated')
      }
    }, REFRESH_MS)
  }, [stopRefresh])

  // Check existing session on mount
  useEffect(() => {
    api('GET', '/users/me')
      .then(data => {
        setUser(data)
        setStatus('authenticated')
        startRefresh()
      })
      .catch(() => setStatus('unauthenticated'))

    return () => stopRefresh()
  }, [])

  // Call this after a successful login API call
  const login = useCallback(async () => {
    const data = await api('GET', '/users/me')
    setUser(data)
    setStatus('authenticated')
    startRefresh()
  }, [startRefresh])

  const logout = useCallback(async () => {
    stopRefresh()
    try { await api('POST', '/users/logout') } catch {}
    setUser(null)
    setStatus('unauthenticated')
  }, [stopRefresh])

  return { user, status, login, logout }
}
