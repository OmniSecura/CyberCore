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
  list:         (slug)                 => api.get(`/organizations/members/${slug}/members`),
  updateRole:   (slug, userId, role)   => api.patch(`/organizations/members/${slug}/members/${userId}`, { role }),
  remove:       (slug, userId)         => api.delete(`/organizations/members/${slug}/members/${userId}`),
}

export const inviteApi = {
  list:    (slug)                 => api.get(`/organizations/members/${slug}/invites`),
  create:  (slug, email, role)    => api.post(`/organizations/members/${slug}/invites`, { email, role }),
  revoke:  (slug, inviteId)       => api.delete(`/organizations/members/${slug}/invites/${inviteId}`),
  accept:  (token)                => api.post('/invites/accept', { token }),
}

// ── Email ─────────────────────────────────────────────────────────────────
export const emailApi = {
  verifyEmail:          (token)    => api.post("/email/verify", { token }),
  requestPasswordReset: (email)    => api.post("/email/reset-password/request", { email }),
  confirmPasswordReset: (data)     => api.post("/email/reset-password/confirm", data),
};
