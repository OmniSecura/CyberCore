import threading
from datetime import datetime, timezone

_blacklist: dict[str, int] = {}   # jti -> exp timestamp
_lock = threading.Lock()


def blacklist_token(jti: str, exp_timestamp: int) -> None:
    """Add a token JTI to the blacklist."""
    with _lock:
        _blacklist[jti] = exp_timestamp
        _cleanup()


def is_blacklisted(jti: str) -> bool:
    """Return True if the token has been revoked."""
    with _lock:
        return jti in _blacklist


def _cleanup() -> None:
    """
    Remove expired entries so the dict doesn't grow forever.
    Called automatically on every blacklist_token() call.
    """
    now = int(datetime.now(timezone.utc).timestamp())
    expired = [jti for jti, exp in _blacklist.items() if exp < now]
    for jti in expired:
        del _blacklist[jti]