"""
Singleton cyberlog client for auth-service.

If CYBERLOG_API_KEY is not set the service still starts — logs fall back to
the stdlib logger so nothing crashes.  Set the env var to start shipping logs
to CyberCore.
"""
from __future__ import annotations

import logging
import os
from typing import Any

_api_key = os.getenv("CYBERLOG_API_KEY", "")


if _api_key:
    from cyberlog import CyberLogCore

    log = CyberLogCore(
        api_key=_api_key,
        project="auth-service",
        validate_on_init=False,
    )
else:
    # ── No-op fallback — mirrors CyberLogCore's public API ───────────────────
    _stdlib = logging.getLogger("cyberlog.auth-service")

    class _NoopLog:
        def debug   (self, msg: str, **kw: Any) -> None: _stdlib.debug   (msg, extra=kw)
        def info    (self, msg: str, **kw: Any) -> None: _stdlib.info    (msg, extra=kw)
        def warning (self, msg: str, **kw: Any) -> None: _stdlib.warning (msg, extra=kw)
        def error   (self, msg: str, **kw: Any) -> None: _stdlib.error   (msg, extra=kw)
        def critical(self, msg: str, **kw: Any) -> None: _stdlib.critical(msg, extra=kw)
        def bind    (self, **kw: Any) -> "_NoopLog":     return self

    log: Any = _NoopLog()
