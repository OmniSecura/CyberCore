import os

APP_NAME        = "LogService"
APP_DESCRIPTION = "CyberCore log ingestion + retrieval API"
APP_VERSION     = "0.1.0"

# Comma separated list of trusted origins for CORS.
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:80,http://localhost:3000",
).split(",")

# Redis — DB 2, separate from Celery (0) and the auth-service blacklist (1).
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/2")

# Redis list used as a buffer between log-service and log-consumer.
LOG_QUEUE_KEY = os.getenv("LOG_QUEUE_KEY", "cyberlog:queue")

# Redis key prefix for cached API-key → org-info lookups.
API_KEY_CACHE_PREFIX = "apikey:"

# How long a validated API key stays cached in Redis (seconds).
API_KEY_CACHE_TTL = int(os.getenv("API_KEY_CACHE_TTL", "300"))

# Max number of log entries the library can send in a single ingest call.
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "500"))
