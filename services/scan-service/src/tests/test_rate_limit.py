"""
Rate limit tests for scan-service.

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

class TestScanLimitOrdering:
    @staticmethod
    def _parse(limit_str: str) -> tuple[int, str]:
        count, period = limit_str.split("/")
        return int(count), period

    def test_upload_scan_most_restrictive_submission(self):
        upload_n, upload_p = self._parse(settings.POST_SCANS_UPLOAD)
        git_n, git_p = self._parse(settings.POST_SCANS_GIT)
        if upload_p == git_p:
            assert upload_n <= git_n, (
                "File upload scans should be at least as restrictive as git scans"
            )

    def test_read_endpoints_more_permissive_than_submit(self):
        get_n, get_p = self._parse(settings.GET_SCANS)
        post_n, post_p = self._parse(settings.POST_SCANS_GIT)
        if get_p == post_p:
            assert get_n >= post_n

    def test_export_more_restrictive_than_list(self):
        export_n, export_p = self._parse(settings.GET_SCANS_EXPORT)
        list_n, list_p = self._parse(settings.GET_SCANS)
        if export_p == list_p:
            assert export_n <= list_n

    def test_cancel_not_more_permissive_than_submit(self):
        cancel_n, cancel_p = self._parse(settings.POST_SCANS_CANCEL)
        submit_n, submit_p = self._parse(settings.POST_SCANS_GIT)
        if cancel_p == submit_p:
            assert cancel_n <= submit_n


# ── 4. parametrized sensitive endpoint tests ──────────────────────────────────

class TestSpecificEndpointLimits:
    @pytest.mark.parametrize("limit_str", [
        settings.POST_SCANS_GIT,
        settings.POST_SCANS_WEB,
        settings.POST_SCANS_UPLOAD,
        settings.POST_SCANS_CANCEL,
        settings.DELETE_SCANS,
    ])
    def test_scan_submission_limit_is_applied(self, limit_str):
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
