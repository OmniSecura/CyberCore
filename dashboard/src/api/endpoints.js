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
  findings: (slug, jobId, { offset = 0, limit = 200, severity, tool } = {}) => {
    const qs = new URLSearchParams({ offset, limit })
    if (severity) qs.set('severity', severity)
    if (tool)     qs.set('tool', tool)
    return api.get(`/scans/organizations/${slug}/scans/${jobId}/findings?${qs}`)
  },
  submitGit: (slug, data)  => api.post(`/scans/organizations/${slug}/scans/git`, data),
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
}

// ── Email ─────────────────────────────────────────────────────────────────
export const emailApi = {
  verifyEmail:          (token)    => api.post("/email/verify", { token }),
  requestPasswordReset: (email)    => api.post("/email/reset-password/request", { email }),
  confirmPasswordReset: (data)     => api.post("/email/reset-password/confirm", data),
};
