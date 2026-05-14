import os

APP_NAME        = "OrganizationService"
APP_DESCRIPTION = ""
APP_VERSION     = "0.1.0"

# Per-owner cap on active free-plan organizations. Override via env var.
try:
    MAX_FREE_ORGS_PER_OWNER = int(os.getenv("MAX_FREE_ORGS_PER_OWNER", "3"))
except ValueError:
    MAX_FREE_ORGS_PER_OWNER = 3

# Comma separated list of trusted origins for CORS. If not provided, defaults to
# ``http://localhost`` which is suitable for local development.
# ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS","http://127.0.0.1:8001").split(",")
