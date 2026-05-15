import os

# Redis / Celery
CELERY_BROKER_URL      = os.getenv("CELERY_BROKER_URL",      "redis://localhost:6379/0")
CELERY_RESULT_BACKEND  = os.getenv("CELERY_RESULT_BACKEND",  "redis://localhost:6379/0")

# Filesystem scratch space for clones and zip extractions
SCAN_WORKSPACE_DIR = os.getenv("SCAN_WORKSPACE_DIR", "/tmp/cybercore/scans")
SCAN_UPLOAD_DIR    = os.getenv("SCAN_UPLOAD_DIR",    "/tmp/cybercore/uploads")

# OWASP ZAP daemon — used by the DAST runner. The daemon is the long-running
# proxy + scanner; we talk to it over its REST API. The API key is mandatory
# in production to prevent anyone on the same network from driving the
# scanner against arbitrary targets.
ZAP_HOST    = os.getenv("ZAP_HOST",    "zap")
ZAP_PORT    = int(os.getenv("ZAP_PORT", "8090"))
ZAP_API_KEY = os.getenv("ZAP_API_KEY", "")

# Per-phase timeouts (minutes). The hard task limit lives on the Celery task
# decorator — these are softer fences that let one phase abort without
# killing the whole job.
ZAP_TIMEOUT_SPIDER_MIN = int(os.getenv("ZAP_TIMEOUT_SPIDER_MIN", "10"))
ZAP_TIMEOUT_AJAX_SPIDER_MIN = int(os.getenv("ZAP_TIMEOUT_AJAX_SPIDER_MIN", "20"))
ZAP_TIMEOUT_PASSIVE_MIN = int(os.getenv("ZAP_TIMEOUT_PASSIVE_MIN", "10"))
ZAP_TIMEOUT_ACTIVE_MIN = int(os.getenv("ZAP_TIMEOUT_ACTIVE_MIN", "45"))
ZAP_TIMEOUT_OPENAPI_MIN = int(os.getenv("ZAP_TIMEOUT_OPENAPI_MIN", "5"))

# How often the runner polls a long-running ZAP operation and pushes progress
# back to the ScanJob row. 5 s is a good balance between responsive UI and
# DB write pressure on a worker doing many concurrent scans.
ZAP_POLL_INTERVAL_SEC = int(os.getenv("ZAP_POLL_INTERVAL_SEC", "5"))
