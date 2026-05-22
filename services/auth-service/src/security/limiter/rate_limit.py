import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Use Redis in production (set RATE_LIMIT_STORAGE_URI=redis://...).
# Falls back to in-process memory when the variable is absent — safe for
# single-instance dev/test but does not share counts across workers.
_STORAGE_URI = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

limiter = Limiter(key_func=get_remote_address, storage_uri=_STORAGE_URI)

__all__ = ["limiter", "RateLimitExceeded", "_rate_limit_exceeded_handler"]
