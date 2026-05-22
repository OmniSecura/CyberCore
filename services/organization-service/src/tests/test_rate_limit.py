"""
Rate limit tests for organization-service.

Builds a minimal in-memory FastAPI app with the same limit strings defined
in security.limiter.settings so no database, Redis, or real dependencies
are needed.
"""
import inspect
import re

import pytest
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.testclient import TestClient

from src.security.limiter import settings

_LIMIT_RE = re.compile(r"^\d+/(second|minute|hour|day)$")


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_app(*limit_strings: str) -> tuple[FastAPI, Limiter]:
    lim = Limiter(key_func=get_remote_address, storage_uri="memory://")
    app = FastAPI()
    app.state.limiter = lim
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    for idx, limit_str in enumerate(limit_strings):
        def _make_endpoint(ls: str, i: int):
            @app.get(f"/probe/{i}")
            @lim.limit(ls)
            def _probe_endpoint(request: Request):
                return {"ok": True}
            _probe_endpoint.__name__ = f"_probe_{i}"
        _make_endpoint(limit_str, idx)

    return app, lim


@pytest.fixture()
def client_2pm():
    app, lim = _make_app("2/minute")
    with TestClient(app, base_url="http://testserver") as c:
        yield c
    lim._storage.reset()


# ── 1. settings format ────────────────────────────────────────────────────────

class TestSettingsFormat:
    def test_all_constants_are_valid_limit_strings(self):
        for name, value in inspect.getmembers(settings, lambda v: isinstance(v, str)):
            if name.startswith("_"):
                continue
            assert _LIMIT_RE.match(value), (
                f"settings.{name} = {value!r} is not a valid rate limit string"
            )


# ── 2. basic enforcement ──────────────────────────────────────────────────────

class TestRateLimitEnforcement:
    def test_requests_within_limit_succeed(self, client_2pm):
        for _ in range(2):
            assert client_2pm.get("/probe/0").status_code == 200

    def test_request_over_limit_returns_429(self, client_2pm):
        client_2pm.get("/probe/0")
        client_2pm.get("/probe/0")
        r = client_2pm.get("/probe/0")
        assert r.status_code == 429

    def test_429_response_contains_error(self, client_2pm):
        client_2pm.get("/probe/0")
        client_2pm.get("/probe/0")
        body = client_2pm.get("/probe/0").json()
        assert "error" in body

    def test_independent_endpoints_have_separate_counters(self):
        app, lim = _make_app("2/minute", "3/minute")
        try:
            with TestClient(app, base_url="http://testserver") as c:
                c.get("/probe/0")
                c.get("/probe/0")
                assert c.get("/probe/0").status_code == 429
                assert c.get("/probe/1").status_code == 200
        finally:
            lim._storage.reset()


# ── 3. service-specific ordering ──────────────────────────────────────────────

class TestOrgLimitOrdering:
    @staticmethod
    def _parse(limit_str: str) -> tuple[int, str]:
        count, period = limit_str.split("/")
        return int(count), period

    def test_create_org_not_more_permissive_than_list_orgs(self):
        post_n, post_p = self._parse(settings.POST_ORGANIZATIONS)
        get_n, get_p = self._parse(settings.GET_ORGANIZATIONS_MY)
        if post_p == get_p:
            assert post_n <= get_n

    def test_destructive_ops_not_more_permissive_than_reads(self):
        del_n, del_p = self._parse(settings.DELETE_ORGANIZATIONS_SLUG)
        get_n, get_p = self._parse(settings.GET_ORGANIZATIONS_SLUG)
        if del_p == get_p:
            assert del_n <= get_n

    def test_transfer_ownership_is_most_restrictive_mutating(self):
        transfer_n, transfer_p = self._parse(settings.PATCH_ORGANIZATIONS_TRANSFER_OWNERSHIP)
        patch_n, patch_p = self._parse(settings.PATCH_ORGANIZATIONS_SLUG)
        if transfer_p == patch_p:
            assert transfer_n <= patch_n

    def test_invite_creation_more_restrictive_than_listing(self):
        post_n, post_p = self._parse(settings.POST_ORGANIZATIONS_INVITES)
        get_n, get_p = self._parse(settings.GET_ORGANIZATIONS_INVITES)
        if post_p == get_p:
            assert post_n <= get_n


# ── 4. parametrized sensitive endpoint tests ──────────────────────────────────

class TestSpecificEndpointLimits:
    @pytest.mark.parametrize("limit_str", [
        settings.POST_ORGANIZATIONS,
        settings.DELETE_ORGANIZATIONS_SLUG,
        settings.PATCH_ORGANIZATIONS_TRANSFER_OWNERSHIP,
        settings.POST_ORGANIZATIONS_INVITES,
    ])
    def test_mutating_endpoint_limit_is_applied(self, limit_str):
        count, _ = limit_str.split("/")
        n = int(count)
        app, lim = _make_app(limit_str)
        try:
            with TestClient(app, base_url="http://testserver") as c:
                for _ in range(n):
                    assert c.get("/probe/0").status_code == 200
                assert c.get("/probe/0").status_code == 429
        finally:
            lim._storage.reset()
