# Rate limit settings for auth-service.
# Format: "<count>/<period>"  where period ∈ {second, minute, hour, day}

# POST /api/v1/users/register
POST_USERS_REGISTER = "5/minute"

# POST /api/v1/users/login
POST_USERS_LOGIN = "10/minute"

# POST /api/v1/users/refresh
POST_USERS_REFRESH = "30/minute"

# POST /api/v1/users/logout
POST_USERS_LOGOUT = "30/minute"

# GET /api/v1/users/me
GET_USERS_ME = "60/minute"

# POST /api/v1/users/lookup
POST_USERS_LOOKUP = "30/minute"

# POST /api/v1/users/me/resend-verification
POST_USERS_ME_RESEND_VERIFICATION = "3/minute"

# DELETE /api/v1/users/me
DELETE_USERS_ME = "5/minute"

# DELETE /api/v1/users/admin/{user_id}
DELETE_USERS_ADMIN = "20/minute"

# POST /api/v1/email/verify
POST_EMAIL_VERIFY = "10/minute"

# POST /api/v1/email/reset-password/request
POST_EMAIL_RESET_PASSWORD_REQUEST = "5/minute"

# POST /api/v1/email/reset-password/confirm
POST_EMAIL_RESET_PASSWORD_CONFIRM = "10/minute"
