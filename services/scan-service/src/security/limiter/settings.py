# Rate limit settings for scan-service.
# Format: "<count>/<period>"  where period ∈ {second, minute, hour, day}

# POST /api/v1/organizations/{slug}/scans/git
POST_SCANS_GIT = "10/minute"

# POST /api/v1/organizations/{slug}/scans/web
POST_SCANS_WEB = "10/minute"

# POST /api/v1/organizations/{slug}/scans/upload
POST_SCANS_UPLOAD = "5/minute"

# GET /api/v1/organizations/{slug}/scans
GET_SCANS = "60/minute"

# GET /api/v1/organizations/{slug}/scans/summary
GET_SCANS_SUMMARY = "30/minute"

# GET /api/v1/organizations/{slug}/scans/stats
GET_SCANS_STATS = "30/minute"

# GET /api/v1/organizations/{slug}/scans/{job_id}
GET_SCANS_DETAIL = "60/minute"

# GET /api/v1/organizations/{slug}/scans/{job_id}/findings
GET_SCANS_FINDINGS = "60/minute"

# GET /api/v1/organizations/{slug}/scans/{job_id}/export
GET_SCANS_EXPORT = "10/minute"

# POST /api/v1/organizations/{slug}/scans/{job_id}/cancel
POST_SCANS_CANCEL = "10/minute"

# DELETE /api/v1/organizations/{slug}/scans/{job_id}
DELETE_SCANS = "10/minute"
