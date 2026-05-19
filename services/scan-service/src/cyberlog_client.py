"""
Singleton cyberlog client for scan-service.

Usage anywhere in the service:
    from .cyberlog_client import log

    log.info("Scan submitted", org_id="...", scan_id="...")

    # With bind() for per-scan context:
    scan_log = log.bind(org_id=org_id, scan_id=job.id, scan_type=job.scan_type)
    scan_log.info("Scan queued", target=job.target_url)
"""
import os

from cyberlog import CyberLogCore

log = CyberLogCore(
    api_key=os.getenv("CYBERLOG_API_KEY", ""),
    project="scan-service",
    validate_on_init=False,
)
