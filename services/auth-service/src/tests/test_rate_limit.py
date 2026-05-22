"""
Rate limit tests for auth-service.

Builds a minimal in-memory FastAPI app with the same limit strings defined
in security.limiter.settings so no database, Redis, or real dependencies
are needed. Tests verify:

  1. All settings constants use the valid "<count>/<period>" format.
  2. The limiter allows requests up to the declared limit.
  3. The limiter returns HTTP 429 once the limit is exceeded.
  4. Independent endpoints do not share counters.
  5. Service-specific ordering expectations (e.g. register ≤ login limit).
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
    """Return a minimal app + fresh in-memory limiter with one probe route per limit."""
    lim = Limiter(key_func=get_remote_address, storage_uri="memory://")
    app = FastAPI()
    app.state.limiter = lim
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    for idx, limit_str in enumerate(limit_strings):
        # Factory captures ls and i to avoid closure-over-loop-variable bug.
        # Unique function name prevents FastAPI duplicate operationId warnings.
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
    """TestClient backed by a '2/minute' limited endpoint."""
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
                # Exhaust /probe/0 (limit: 2)
                c.get("/probe/0")
                c.get("/probe/0")
                assert c.get("/probe/0").status_code == 429
                # /probe/1 still has capacity (limit: 3)
                assert c.get("/probe/1").status_code == 200
        finally:
            lim._storage.reset()

    def test_first_request_always_succeeds(self):
        app, lim = _make_app("1/minute")
        try:
            with TestClient(app, base_url="http://testserver") as c:
                assert c.get("/probe/0").status_code == 200
        finally:
            lim._storage.reset()


# ── 3. service-specific ordering ──────────────────────────────────────────────

class TestAuthLimitOrdering:
    @staticmethod
    def _parse(limit_str: str) -> tuple[int, str]:
        count, period = limit_str.split("/")
        return int(count), period

    def test_register_not_more_permissive_than_login(self):
        reg_n, reg_p = self._parse(settings.POST_USERS_REGISTER)
        log_n, log_p = self._parse(settings.POST_USERS_LOGIN)
        if reg_p == log_p:
            assert reg_n <= log_n, (
                "POST_USERS_REGISTER should be at least as strict as POST_USERS_LOGIN"
            )

    def test_password_reset_request_not_more_permissive_than_login(self):
        rst_n, rst_p = self._parse(settings.POST_EMAIL_RESET_PASSWORD_REQUEST)
        log_n, log_p = self._parse(settings.POST_USERS_LOGIN)
        if rst_p == log_p:
            assert rst_n <= log_n, (
                "Password-reset endpoint should be at least as strict as login"
            )

    def test_resend_verification_is_most_restrictive_authenticated(self):
        rv_n, rv_p = self._parse(settings.POST_USERS_ME_RESEND_VERIFICATION)
        me_n, me_p = self._parse(settings.GET_USERS_ME)
        if rv_p == me_p:
            assert rv_n <= me_n

    def test_read_endpoints_more_permissive_than_write_endpoints(self):
        get_n, get_p = self._parse(settings.GET_USERS_ME)
        post_n, post_p = self._parse(settings.POST_USERS_LOGIN)
        if get_p == post_p:
            assert get_n >= post_n, (
                "GET /me should allow more requests per period than POST /login"
            )


# ── 4. specific endpoint limits work end-to-end ───────────────────────────────

class TestSpecificEndpointLimits:
    @pytest.mark.parametrize("limit_str", [
        settings.POST_USERS_REGISTER,
        settings.POST_USERS_LOGIN,
        settings.POST_EMAIL_RESET_PASSWORD_REQUEST,
    ])
    def test_sensitive_endpoint_limit_is_applied(self, limit_str):
        """Verify that each sensitive endpoint actually blocks after N requests."""
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
