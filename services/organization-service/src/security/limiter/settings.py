# Rate limit settings for organization-service.
# Format: "<count>/<period>"  where period ∈ {second, minute, hour, day}

# POST /api/v1/organizations/
POST_ORGANIZATIONS = "10/minute"

# GET /api/v1/organizations/my
GET_ORGANIZATIONS_MY = "60/minute"

# GET /api/v1/organizations/free-cap-status
GET_ORGANIZATIONS_FREE_CAP_STATUS = "60/minute"

# GET /api/v1/organizations/{slug}
GET_ORGANIZATIONS_SLUG = "60/minute"

# PATCH /api/v1/organizations/{slug}
PATCH_ORGANIZATIONS_SLUG = "20/minute"

# DELETE /api/v1/organizations/{slug}
DELETE_ORGANIZATIONS_SLUG = "10/minute"

# PATCH /api/v1/organizations/{slug}/transfer-ownership
PATCH_ORGANIZATIONS_TRANSFER_OWNERSHIP = "5/minute"

# POST /api/v1/organizations/transfer-ownership/accept
POST_ORGANIZATIONS_TRANSFER_OWNERSHIP_ACCEPT = "10/minute"

# POST /api/v1/organizations/{org_id}/reactivate
POST_ORGANIZATIONS_REACTIVATE = "10/minute"

# GET /api/v1/organizations/members/{slug}/members
GET_ORGANIZATIONS_MEMBERS = "60/minute"

# PATCH /api/v1/organizations/members/{slug}/members/{user_id}
PATCH_ORGANIZATIONS_MEMBERS = "20/minute"

# DELETE /api/v1/organizations/members/{slug}/members/{user_id}
DELETE_ORGANIZATIONS_MEMBERS = "20/minute"

# POST /api/v1/organizations/members/{slug}/invites
POST_ORGANIZATIONS_INVITES = "10/minute"

# GET /api/v1/organizations/members/{slug}/invites
GET_ORGANIZATIONS_INVITES = "60/minute"

# DELETE /api/v1/organizations/members/{slug}/invites/{invite_id}
DELETE_ORGANIZATIONS_INVITES = "20/minute"

# POST /api/v1/invites/accept
POST_INVITES_ACCEPT = "10/minute"

# GET /api/v1/organizations/roles/{slug}
GET_ROLES = "60/minute"

# POST /api/v1/organizations/roles/{slug}
POST_ROLES = "10/minute"

# PATCH /api/v1/organizations/roles/{slug}/{role_id}
PATCH_ROLES = "20/minute"

# DELETE /api/v1/organizations/roles/{slug}/{role_id}
DELETE_ROLES = "20/minute"

# GET /api/v1/organizations/roles/privileges
GET_ROLES_PRIVILEGES = "60/minute"

# GET /api/v1/organizations/roles/{slug}/my-privileges
GET_ROLES_MY_PRIVILEGES = "60/minute"
