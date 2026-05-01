const BASE = '/api/v1'

/**
 * Thin fetch wrapper.
 * - Sends credentials (cookies) on every request
 * - Throws an enriched error with { status, data } on non-2xx responses
 */
export async function api(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    credentials: 'include',           // send httpOnly cookies automatically
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    const err = new Error(data?.detail || 'Request failed')
    err.status = res.status
    err.data   = data
    throw err
  }

  return data
}
