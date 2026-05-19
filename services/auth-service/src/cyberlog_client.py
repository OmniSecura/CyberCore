"""
Singleton cyberlog client for auth-service.

Usage anywhere in the service:
    from .cyberlog_client import log

    log.info("User logged in", user_id="abc")

    # With bind() for per-request context:
    req_log = log.bind(user_id=user.id, email=user.email)
    req_log.info("Login successful")
"""
import os

from cyberlog import CyberLogCore

# validate_on_init=False — if the log-service is temporarily down,
# auth-service still starts and handles requests normally.
# Logs will be buffered and retried automatically.
log = CyberLogCore(
    api_key=os.getenv("CYBERLOG_API_KEY", ""),
    project="auth-service",
    validate_on_init=False,
)
