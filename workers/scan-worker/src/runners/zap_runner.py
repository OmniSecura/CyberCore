"""
OWASP ZAP runner — drives a long-running ZAP daemon over its REST API.

Phases the runner can execute:

  • spider      — classic crawler, discovers static endpoints / forms
  • passive     — analyses traffic already in the spider's queue (no attacks)
  • active      — sends real attack payloads (only when profile='active')

Each long-running operation has its own poller that pushes progress (0–100)
back into the caller via a `progress_cb` so the API layer can surface it on
the ScanJob row.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

import httpx

from ..global_settings import (
    ZAP_HOST,
    ZAP_PORT,
    ZAP_API_KEY,
    ZAP_TIMEOUT_SPIDER_MIN,
    ZAP_TIMEOUT_AJAX_SPIDER_MIN,
    ZAP_TIMEOUT_PASSIVE_MIN,
    ZAP_TIMEOUT_ACTIVE_MIN,
    ZAP_TIMEOUT_OPENAPI_MIN,
    ZAP_POLL_INTERVAL_SEC,
)

log = logging.getLogger(__name__)

ProgressCb = Callable[[str, int], None]


class ZapError(RuntimeError):
    pass


def _base_url() -> str:
    return f"http://{ZAP_HOST}:{ZAP_PORT}"


def _client() -> httpx.Client:
    # 30 s per HTTP call is plenty — every long operation is implemented as
    # poll + sleep, not as a single blocking request.
    return httpx.Client(base_url=_base_url(), timeout=30.0)


def _get(client: httpx.Client, path: str, **params) -> dict:
    """
    Wrap a ZAP JSON API call. ZAP returns 200 with a JSON body even on logical
    errors, so we have to inspect the body. `apikey` is appended to every
    request — without it the daemon rejects mutating calls.
    """
    if ZAP_API_KEY:
        params["apikey"] = ZAP_API_KEY
    r = client.get(path, params=params)
    if r.status_code >= 400:
        raise ZapError(f"ZAP {path} → HTTP {r.status_code}: {r.text[:300]}")
    try:
        data = r.json()
    except ValueError as exc:
        raise ZapError(f"ZAP {path} returned non-JSON: {r.text[:200]}") from exc
    return data


def _wait_for_daemon(client: httpx.Client, attempts: int = 60) -> None:
    """
    The ZAP daemon takes 10–30 s to come up. Tasks scheduled the instant the
    container starts will otherwise hit a connection refused; poll the version
    endpoint until it answers.
    """
    last_err: Exception | None = None
    for _ in range(attempts):
        try:
            data = _get(client, "/JSON/core/view/version/")
            log.info("ZAP daemon ready, version=%s", data.get("version"))
            return
        except Exception as exc:
            last_err = exc
            time.sleep(1.0)
    raise ZapError(f"ZAP daemon not reachable after {attempts}s: {last_err}")


def _host_regex_prefix(target_url: str) -> str:
    """
    Build the regex prefix that anchors a pattern to the target's host. Used
    both by the in-scope include pattern and by the exclude-path translator,
    so they stay consistent.
    """
    from urllib.parse import urlparse
    parsed = urlparse(target_url)
    host = parsed.hostname or ""
    return rf"https?://{host.replace('.', r'\.')}(:\d+)?"


def _exclude_path_to_regex(raw: str, host_prefix: str) -> str:
    """
    Translate a user-supplied exclude entry into a full ZAP regex pattern.

    Rules:
      • starts with "/"  → treated as a URL path. We escape regex metacharacters,
                           then turn shell-style "*" back into ".*" so the user
                           can write "/admin/*" naturally. Anchored on the
                           target host.
      • otherwise        → treated as a raw regex, passed through verbatim.
                           Lets power users write things like
                           "^.*/(logout|signout)$" if they really want to.
    """
    import re
    s = raw.strip()
    if not s.startswith("/"):
        return s
    # Escape everything, then unescape the "*" -> ".*" sugar.
    escaped = re.escape(s).replace(r"\*", ".*")
    return f"{host_prefix}{escaped}"


def _new_context(
    client: httpx.Client,
    name: str,
    target_url: str,
    exclude_paths: list[str] | None = None,
) -> str:
    """
    ZAP contexts scope a scan to one or more URL patterns. We create a fresh
    context per job, include the target's host, and (optionally) add exclude
    patterns so the spider/active scanner won't visit logout/destroy/etc URLs.
    """
    _get(client, "/JSON/context/action/newContext/", contextName=name)
    host_prefix = _host_regex_prefix(target_url)
    _get(
        client,
        "/JSON/context/action/includeInContext/",
        contextName=name,
        regex=f"{host_prefix}/.*",
    )
    for raw in exclude_paths or []:
        pattern = _exclude_path_to_regex(raw, host_prefix)
        try:
            _get(
                client,
                "/JSON/context/action/excludeFromContext/",
                contextName=name,
                regex=pattern,
            )
            log.info("Excluded from scope: %s", pattern)
        except ZapError as exc:
            # Bad regex from the user shouldn't kill the whole scan — log and
            # carry on without that exclusion.
            log.warning("Invalid exclude regex %r ignored: %s", pattern, exc)
    # Pull the context id back so the spider/active calls can reference it.
    data = _get(client, "/JSON/context/view/context/", contextName=name)
    return str(data["context"]["id"])


def _poll(
    client: httpx.Client,
    status_path: str,
    timeout_min: int,
    phase: str,
    progress_cb: ProgressCb | None,
    **status_params,
) -> None:
    """
    Generic ZAP poll loop. Polls `status_path` (e.g. /JSON/spider/view/status/)
    until it returns "100", forwarding progress through `progress_cb`.
    Bails out at `timeout_min` so a wedged scan can't pin the worker forever.
    """
    deadline = time.monotonic() + timeout_min * 60
    last_reported = -1
    while True:
        data = _get(client, status_path, **status_params)
        try:
            pct = int(data.get("status", "0"))
        except (TypeError, ValueError):
            pct = 0
        if pct != last_reported and progress_cb:
            progress_cb(phase, pct)
            last_reported = pct
        if pct >= 100:
            return
        if time.monotonic() > deadline:
            log.warning("Phase %s timed out at %d%% (limit %dm)", phase, pct, timeout_min)
            return
        time.sleep(ZAP_POLL_INTERVAL_SEC)


def _run_spider(
    client: httpx.Client,
    context_name: str,
    target_url: str,
    progress_cb: ProgressCb | None,
) -> None:
    data = _get(
        client,
        "/JSON/spider/action/scan/",
        url=target_url,
        contextName=context_name,
        recurse="true",
    )
    scan_id = data.get("scan")
    if scan_id is None:
        raise ZapError(f"Spider start failed: {data}")
    _poll(
        client,
        "/JSON/spider/view/status/",
        ZAP_TIMEOUT_SPIDER_MIN,
        "spider",
        progress_cb,
        scanId=scan_id,
    )


def _run_ajax_spider(
    client: httpx.Client,
    context_name: str,
    target_url: str,
    progress_cb: ProgressCb | None,
) -> None:
    """
    Headless-browser crawl. Needed for SPAs — the classic spider only sees
    the initial HTML and misses everything React/Vue/Angular renders.

    AJAX spider's API is shaped differently from the classic spider:
      • No numeric scan id, just one global session.
      • Status is "running" / "stopped" (not 0–100). We map that to 50/100 for
        the progress callback so the UI still gets a heartbeat.
    """
    _get(
        client,
        "/JSON/ajaxSpider/action/scan/",
        url=target_url,
        contextName=context_name,
        inScope="true",
    )
    deadline = time.monotonic() + ZAP_TIMEOUT_AJAX_SPIDER_MIN * 60
    started = False
    while True:
        data = _get(client, "/JSON/ajaxSpider/view/status/")
        running = str(data.get("status", "")).lower() == "running"
        if running and not started:
            started = True
            if progress_cb:
                progress_cb("ajax_spider", 25)
        if not running:
            if progress_cb:
                progress_cb("ajax_spider", 100)
            return
        if time.monotonic() > deadline:
            log.warning("AJAX spider timed out (limit %dm), stopping",
                        ZAP_TIMEOUT_AJAX_SPIDER_MIN)
            # Best-effort stop so the daemon's browser pool gets released.
            try:
                _get(client, "/JSON/ajaxSpider/action/stop/")
            except Exception:
                pass
            return
        if progress_cb:
            progress_cb("ajax_spider", 50)
        time.sleep(ZAP_POLL_INTERVAL_SEC)


def _run_openapi_import(
    client: httpx.Client,
    spec_url: str,
    context_name: str,
    progress_cb: ProgressCb | None,
) -> None:
    """
    Pull an OpenAPI/Swagger spec into ZAP. The OpenAPI add-on parses every
    operation in the spec and pushes the endpoint+method+example-params into
    ZAP's site tree, so the passive/active stages can hit them without any
    crawl.

    The import is essentially synchronous on ZAP's side — it returns once
    parsing is done — but we expose progress 0→100 around it so the UI shows
    the phase happened.
    """
    if progress_cb:
        progress_cb("openapi", 10)
    data = _get(
        client,
        "/JSON/openapi/action/importUrl/",
        url=spec_url,
        contextName=context_name,
    )
    # ZAP returns {"Result":"OK"} on success or a list of parser errors. We
    # surface non-OK as a warning but keep scanning — partial coverage is
    # still useful.
    result = data.get("Result") or data.get("result")
    if result and str(result).upper() != "OK":
        log.warning("OpenAPI import returned non-OK: %s", data)
    if progress_cb:
        progress_cb("openapi", 100)
    # Safety belt: if the daemon is still parsing in the background, give it
    # a short grace period before passive scan starts pulling alerts.
    deadline = time.monotonic() + ZAP_TIMEOUT_OPENAPI_MIN * 60
    while time.monotonic() < deadline:
        # No dedicated status endpoint — sleep one poll cycle and assume done.
        time.sleep(ZAP_POLL_INTERVAL_SEC)
        return


def _run_passive(client: httpx.Client, progress_cb: ProgressCb | None) -> None:
    """
    The passive scanner runs in the background as the spider feeds it traffic.
    By the time spider returns 100% there is usually still a backlog of records
    to analyse — wait for the queue to drain.
    """
    deadline = time.monotonic() + ZAP_TIMEOUT_PASSIVE_MIN * 60
    while True:
        data = _get(client, "/JSON/pscan/view/recordsToScan/")
        try:
            remaining = int(data.get("recordsToScan", "0"))
        except (TypeError, ValueError):
            remaining = 0
        if remaining == 0:
            if progress_cb:
                progress_cb("passive", 100)
            return
        if progress_cb:
            # We don't know the start size; report 0 vs ongoing as a sentinel.
            progress_cb("passive", 50)
        if time.monotonic() > deadline:
            log.warning("Passive scan drain timed out, %d records still queued", remaining)
            return
        time.sleep(ZAP_POLL_INTERVAL_SEC)


def _run_active(
    client: httpx.Client,
    context_id: str,
    target_url: str,
    progress_cb: ProgressCb | None,
) -> None:
    data = _get(
        client,
        "/JSON/ascan/action/scan/",
        url=target_url,
        contextId=context_id,
        recurse="true",
        inScopeOnly="true",
    )
    scan_id = data.get("scan")
    if scan_id is None:
        raise ZapError(f"Active scan start failed: {data}")
    _poll(
        client,
        "/JSON/ascan/view/status/",
        ZAP_TIMEOUT_ACTIVE_MIN,
        "active",
        progress_cb,
        scanId=scan_id,
    )


def _collect_alerts(client: httpx.Client, target_url: str) -> list[dict]:
    """
    Pull all alerts in pages of 200. Some ZAP installs cap a single response
    so we never assume the full list fits in one call.
    """
    PAGE = 200
    out: list[dict] = []
    offset = 0
    while True:
        data = _get(
            client,
            "/JSON/core/view/alerts/",
            baseurl=target_url,
            start=offset,
            count=PAGE,
        )
        chunk = data.get("alerts", []) or []
        out.extend(chunk)
        if len(chunk) < PAGE:
            return out
        offset += PAGE


def _cleanup_context(client: httpx.Client, context_name: str) -> None:
    """Best-effort — never fail a completed scan because cleanup hiccuped."""
    try:
        _get(client, "/JSON/context/action/removeContext/", contextName=context_name)
    except Exception as exc:
        log.warning("ZAP context cleanup failed (%s): %s", context_name, exc)


def run(
    target_url: str,
    profile: str,
    context_name: str,
    progress_cb: ProgressCb | None = None,
    *,
    discovery_mode: str = "spider",
    openapi_url: str | None = None,
    exclude_paths: list[str] | None = None,
) -> list[dict]:
    """
    Run a full DAST sequence and return the raw ZAP alerts list.

    `profile`:
      • "passive" → discovery + passive only
      • "active"  → discovery + passive + active scan

    `discovery_mode` controls how endpoints get into ZAP's site tree before
    passive/active stages run:
      • "spider"       → classic HTTP crawler
      • "ajax_spider"  → headless browser (SPA-aware)
      • "openapi"      → import an OpenAPI spec from `openapi_url`

    `exclude_paths` are user-supplied path/glob/regex patterns kept out of
    scope — see `_exclude_path_to_regex` for the input shapes.

    `progress_cb(phase, percent)` is invoked whenever the percentage changes;
    use it to mirror progress into the job row.
    """
    if profile not in ("passive", "active"):
        raise ZapError(f"Unknown DAST profile: {profile!r}")
    if discovery_mode not in ("spider", "ajax_spider", "openapi"):
        raise ZapError(f"Unknown discovery_mode: {discovery_mode!r}")
    if discovery_mode == "openapi" and not openapi_url:
        raise ZapError("openapi_url required when discovery_mode='openapi'")

    with _client() as client:
        _wait_for_daemon(client)
        context_id = _new_context(
            client,
            context_name,
            target_url,
            exclude_paths=exclude_paths,
        )
        try:
            # ── Discovery phase ────────────────────────────────────────────
            if discovery_mode == "spider":
                _run_spider(client, context_name, target_url, progress_cb)
            elif discovery_mode == "ajax_spider":
                _run_ajax_spider(client, context_name, target_url, progress_cb)
            else:  # openapi
                _run_openapi_import(client, openapi_url, context_name, progress_cb)

            # ── Always-on passive drain ────────────────────────────────────
            _run_passive(client, progress_cb)

            # ── Optional active scan ──────────────────────────────────────
            if profile == "active":
                _run_active(client, context_id, target_url, progress_cb)

            return _collect_alerts(client, target_url)
        finally:
            _cleanup_context(client, context_name)
