const BASE = '/api/v1'

/**
 * Thin fetch wrapper.
 * - Sends credentials (cookies) on every request
 * - Throws an enriched error with { status, data } on non-2xx responses
 *
 * `opts.headers` lets callers tack on extra headers (e.g. `X-Org-Id` for
 * the log-service endpoints which need an explicit org context).
 */
export async function api(method, path, body, opts = {}) {
  const headers = {
    ...(body ? { 'Content-Type': 'application/json' } : {}),
    ...(opts.headers || {}),
  }

  const res = await fetch(BASE + path, {
    method,
    credentials: 'include',           // send httpOnly cookies automatically
    headers,
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

api.get    = (path, body, opts)  => api('GET',    path, body, opts)
api.post   = (path, body, opts)  => api('POST',   path, body, opts)
api.patch  = (path, body, opts)  => api('PATCH',  path, body, opts)
api.put    = (path, body, opts)  => api('PUT',    path, body, opts)
api.delete = (path, body, opts)  => api('DELETE', path, body, opts)
