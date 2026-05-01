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

// ── Email ─────────────────────────────────────────────────────────────────
export const emailApi = {
  verifyEmail:          (token)    => api.post("/email/verify", { token }),
  requestPasswordReset: (email)    => api.post("/email/reset-password/request", { email }),
  confirmPasswordReset: (data)     => api.post("/email/reset-password/confirm", data),
};
