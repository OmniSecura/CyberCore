import os

APP_NAME        = "ScanService"
APP_DESCRIPTION = "SAST / DAST scan orchestrator for CyberCore"
APP_VERSION     = "0.1.0"

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
