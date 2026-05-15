import os
import sys
from celery import Celery
from .global_settings import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# prefork uses POSIX semaphores that Windows doesn't support — fall back to solo
_DEFAULT_POOL = "solo" if sys.platform == "win32" else "prefork"

celery_app = Celery(
    "scan_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["src.tasks.sast", "src.tasks.dast"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_pool=_DEFAULT_POOL,
    task_routes={
        "scan_worker.tasks.sast.run_sast_scan": {"queue": "sast"},
        "scan_worker.tasks.dast.run_dast_scan": {"queue": "dast"},
    },
    result_expires=86400,         # keep results in Redis for 24 h
)
