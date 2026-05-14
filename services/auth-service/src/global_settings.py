import os

APP_NAME        = "AuthService"
APP_DESCRIPTION = ""
APP_VERSION     = "0.1.0"

# Comma separated list of trusted origins for CORS. If not provided, defaults to
# ``http://localhost`` which is suitable for local development.
# ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS","http://127.0.0.1:8001").split(",")

# Redis — used by the token blacklist so revocations survive service restarts.
# Use DB 1 to stay separate from Celery (which defaults to DB 0).
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
