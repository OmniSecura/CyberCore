import { useState, useCallback } from 'react'
import { api } from '../api/client'

/**
 * Wraps an API call with loading + error state.
 *
 * Usage:
 *   const { call, loading, error } = useApi()
 *   const data = await call('POST', '/users/login', { email, password })
 */
export function useApi() {
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const call = useCallback(async (method, path, body) => {
    setLoading(true)
    setError(null)
    try {
      return await api(method, path, body)
    } catch (err) {
      setError(err)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { call, loading, error }
}
