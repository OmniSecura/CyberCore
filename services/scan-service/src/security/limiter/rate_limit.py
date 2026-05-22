import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

_STORAGE_URI = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

limiter = Limiter(key_func=get_remote_address, storage_uri=_STORAGE_URI)

__all__ = ["limiter", "RateLimitExceeded", "_rate_limit_exceeded_handler"]
