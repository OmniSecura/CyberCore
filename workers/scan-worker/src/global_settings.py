import os

# Redis / Celery
CELERY_BROKER_URL      = os.getenv("CELERY_BROKER_URL",      "redis://localhost:6379/0")
CELERY_RESULT_BACKEND  = os.getenv("CELERY_RESULT_BACKEND",  "redis://localhost:6379/0")

# Filesystem scratch space for clones and zip extractions
SCAN_WORKSPACE_DIR = os.getenv("SCAN_WORKSPACE_DIR", "/tmp/cybercore/scans")
SCAN_UPLOAD_DIR    = os.getenv("SCAN_UPLOAD_DIR",    "/tmp/cybercore/uploads")
