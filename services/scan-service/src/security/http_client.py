"""
Shared httpx.AsyncClient instances for outbound calls to sibling services.

Constructing a fresh AsyncClient per request opens a new TCP/TLS connection
each time and discards it — slow, and at scale it exhausts ephemeral ports.
A module-level client keeps a connection pool so repeated calls reuse sockets.
"""

from __future__ import annotations

import httpx

# Limits sized for an internal service-to-service hop, not a public API.
_LIMITS = httpx.Limits(max_connections=64, max_keepalive_connections=32)
_TIMEOUT = httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)

_org_client: httpx.AsyncClient | None = None
_auth_client: httpx.AsyncClient | None = None


def get_org_service_client() -> httpx.AsyncClient:
    global _org_client
    if _org_client is None:
        _org_client = httpx.AsyncClient(limits=_LIMITS, timeout=_TIMEOUT)
    return _org_client


def get_auth_service_client() -> httpx.AsyncClient:
    global _auth_client
    if _auth_client is None:
        _auth_client = httpx.AsyncClient(limits=_LIMITS, timeout=_TIMEOUT)
    return _auth_client


async def close_clients() -> None:
    """Close pooled clients on app shutdown."""
    global _org_client, _auth_client
    if _org_client is not None:
        await _org_client.aclose()
        _org_client = None
    if _auth_client is not None:
        await _auth_client.aclose()
        _auth_client = None
