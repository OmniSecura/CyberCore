import os

APP_NAME        = ""
APP_DESCRIPTION = ""
APP_VERSION     = ""

# Comma separated list of trusted origins for CORS. If not provided, defaults to
# ``http://localhost`` which is suitable for local development.
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS","http://127.0.0.1:8001").split(",")
