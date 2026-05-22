# Rate limit settings for log-service.
# Format: "<count>/<period>"  where period ∈ {second, minute, hour, day}

# POST /api/v1/ingest
POST_INGEST = "120/minute"

# GET /api/v1/logs
GET_LOGS = "60/minute"

# POST /api/v1/api-keys
POST_API_KEYS = "10/minute"

# GET /api/v1/api-keys
GET_API_KEYS = "30/minute"

# DELETE /api/v1/api-keys/{key_id}
DELETE_API_KEYS = "10/minute"

# GET /api/v1/auth/validate
GET_AUTH_VALIDATE = "60/minute"
