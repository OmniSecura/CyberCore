/**
 * api/endpoints.js
 *
 * All API calls in one place.
 * Adding a new feature = adding a function here, nothing else changes.
 */

import { api } from "./client.js";

// ── Auth ──────────────────────────────────────────────────────────────────
export const authApi = {
  register:           (data)     => api.post("/users/register", data),
  login:              (data)     => api.post("/users/login", data),
  logout:             ()         => api.post("/users/logout"),
  refresh:            ()         => api.post("/users/refresh"),
  me:                 ()         => api.get("/users/me"),
  resendVerification: ()         => api.post("/users/me/resend-verification"),
  deleteAccount:      (password) => api.delete("/users/me", { password }),
};

// ── User lookup (batch resolve UUIDs to {id, email, full_name}) ──────────
export const userApi = {
  lookup: (ids) => api.post("/users/lookup", { ids }),
};

// ── Organizations ─────────────────────────────────────────────────────────
export const orgApi = {
  // List paginated — returns { items, total, page, page_size, total_pages }
  list:       ({ page = 1, pageSize = 20 } = {}) =>
                  api.get(`/organizations/my?page=${page}&page_size=${pageSize}`),
  create:     (data)         => api.post('/organizations/', data),
  get:        (slug)         => api.get(`/organizations/${slug}`),
  update:     (slug, data)   => api.patch(`/organizations/${slug}`, data),
  remove:     (slug)         => api.delete(`/organizations/${slug}`),
  reactivate: (orgId, data)  => api.post(`/organizations/${orgId}/reactivate`, data || {}),

  // Returns { owned, max, can_create } — used to gate create/reactivate UI.
  freeCapStatus: () => api.get('/organizations/free-cap-status'),

  // Ownership transfer (owner only)
  transferOwnership:        (slug, newOwnerId) =>
                                api.patch(`/organizations/${slug}/transfer-ownership`, { new_owner_id: newOwnerId }),
  acceptOwnershipTransfer:  (token) =>
                                api.post(`/organizations/transfer-ownership/accept`, { token }),
};

// ── Members & invites ─────────────────────────────────────────────────────
export const memberApi = {
  list:         (slug)                   => api.get(`/organizations/members/${slug}/members`),
  // payload: { role: "admin"|"member"|"viewer" } OR { custom_role_id: "uuid" }
  updateRole:   (slug, userId, payload)  => api.patch(`/organizations/members/${slug}/members/${userId}`, payload),
  remove:       (slug, userId)           => api.delete(`/organizations/members/${slug}/members/${userId}`),
}

export const inviteApi = {
  list:    (slug)                 => api.get(`/organizations/members/${slug}/invites`),
  create:  (slug, email, role)    => api.post(`/organizations/members/${slug}/invites`, { email, role }),
  revoke:  (slug, inviteId)       => api.delete(`/organizations/members/${slug}/invites/${inviteId}`),
  accept:  (token)                => api.post('/invites/accept', { token }),
}

// ── Custom Roles ──────────────────────────────────────────────────────────
export const roleApi = {
  listPrivileges: ()                          => api.get('/organizations/roles/privileges'),
  // Returns { privileges: ["members.view", ...] } for the current user in this org
  myPrivileges:   (slug)                      => api.get(`/organizations/roles/${slug}/my-privileges`),
  list:           (slug)                      => api.get(`/organizations/roles/${slug}`),
  create:         (slug, data)                => api.post(`/organizations/roles/${slug}`, data),
  update:         (slug, roleId, data)        => api.patch(`/organizations/roles/${slug}/${roleId}`, data),
  remove:         (slug, roleId)              => api.delete(`/organizations/roles/${slug}/${roleId}`),
}

// ── Scans ─────────────────────────────────────────────────────────────────────
export const scanApi = {
  list: (slug, { offset = 0, limit = 20, status } = {}) => {
    const qs = new URLSearchParams({ offset, limit })
    if (status) qs.set('status', status)
    return api.get(`/scans/organizations/${slug}/scans?${qs}`)
  },
  get:      (slug, jobId)  => api.get(`/scans/organizations/${slug}/scans/${jobId}`),
  stats:    (slug)         => api.get(`/scans/organizations/${slug}/scans/stats`),
  // Single-call org overview: severity totals + status counts + 8 recent scans.
  summary:  (slug)         => api.get(`/scans/organizations/${slug}/scans/summary`),
  findings: (slug, jobId, { offset = 0, limit = 100, severity, tool } = {}) => {
    const qs = new URLSearchParams({ offset, limit })
    if (severity) qs.set('severity', severity)
    if (tool)     qs.set('tool', tool)
    return api.get(`/scans/organizations/${slug}/scans/${jobId}/findings?${qs}`)
  },
  submitGit: (slug, data)  => api.post(`/scans/organizations/${slug}/scans/git`, data),
  // DAST submit. `data = { name, target_url, profile: 'passive' | 'active' }`
  submitWeb: (slug, data)  => api.post(`/scans/organizations/${slug}/scans/web`, data),
  submitUpload: async (slug, name, file) => {
    const fd = new FormData()
    fd.append('name', name)
    fd.append('file', file)
    const res = await fetch(`/api/v1/scans/organizations/${slug}/scans/upload`, {
      method: 'POST',
      credentials: 'include',
      body: fd,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      const err = new Error(data?.detail || 'Upload failed')
      err.status = res.status
      err.data   = data
      throw err
    }
    return data
  },
  cancel:    (slug, jobId) => api.post(`/scans/organizations/${slug}/scans/${jobId}/cancel`),
  remove:    (slug, jobId) => api.delete(`/scans/organizations/${slug}/scans/${jobId}`),
  // Export returns a downloadable blob, not JSON — we bypass the standard
  // api.* client because it parses JSON and would mangle the HTML body.
  exportReport: async (slug, jobId, format = 'json') => {
    const res = await fetch(
      `/api/v1/scans/organizations/${slug}/scans/${jobId}/export?format=${encodeURIComponent(format)}`,
      { credentials: 'include' }
    )
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      const err = new Error(data?.detail || 'Export failed')
      err.status = res.status
      err.data   = data
      throw err
    }
    // Pull the filename out of Content-Disposition so the saved file keeps
    // the server-generated "cybercore-<name>-<ts>" name instead of getting
    // a random UUID from the browser.
    const cd = res.headers.get('Content-Disposition') || ''
    const match = cd.match(/filename="([^"]+)"/)
    const filename = match?.[1] || `report.${format}`
    const blob = await res.blob()
    return { blob, filename }
  },
}

// ── Email ─────────────────────────────────────────────────────────────────
export const emailApi = {
  verifyEmail:          (token)    => api.post("/email/verify", { token }),
  requestPasswordReset: (email)    => api.post("/email/reset-password/request", { email }),
  confirmPasswordReset: (data)     => api.post("/email/reset-password/confirm", data),
};

// ── Logs (cyberlog SaaS) ──────────────────────────────────────────────────
// Every endpoint scopes to a single organization via the `X-Org-Id` header.
// `orgId` here is the org's UUID (`org.id`), not its slug.
const orgHeaders = (orgId) => ({ headers: { 'X-Org-Id': orgId } });

export const logApi = {
  // Returns { items: LogResponse[], total, limit, offset }
  list: (orgId, { project, level, since, until, limit = 100, offset = 0 } = {}) => {
    const qs = new URLSearchParams({ limit, offset });
    if (project) qs.set('project', project);
    if (level)   qs.set('level', level);
    if (since)   qs.set('since', since);
    if (until)   qs.set('until', until);
    return api.get(`/logs?${qs}`, undefined, orgHeaders(orgId));
  },
};

export const apiKeyApi = {
  // Returns ApiKeyResponse[]
  list:   (orgId)              => api.get(`/api-keys`, undefined, orgHeaders(orgId)),

  // Returns CreateApiKeyResponse (includes plaintext_key — shown ONCE)
  // payload: { name, ttl_days }
  create: (orgId, payload)     => api.post(`/api-keys`, { org_id: orgId, ...payload }, orgHeaders(orgId)),

  revoke: (orgId, keyId)       => api.delete(`/api-keys/${keyId}`, undefined, orgHeaders(orgId)),
};
