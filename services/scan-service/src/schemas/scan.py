from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator, model_validator


# Allowed schemes for the user-supplied repository URL. We deliberately reject
# any other transport (ssh://, ext::, file://, scp-style …) — see the matching
# validator in the worker's git_utils.validate_git_url.
_ALLOWED_GIT_SCHEMES = ("http", "https", "git")
_ALLOWED_WEB_SCHEMES = ("http", "https")
_HOST_RE = re.compile(r"^[A-Za-z0-9.\-]{1,255}$")


def _is_private_or_local(hostname: str) -> bool:
    """
    True when the hostname is a literal IP that points at private/loopback/
    link-local space. DNS names get resolved later by the worker — this is
    just the cheap first-line check that catches `http://127.0.0.1`,
    `http://10.0.0.5`, etc. submitted by the client.
    """
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return hostname.lower() in ("localhost",)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


# ── Request schemas ────────────────────────────────────────────────────────────

class SubmitGitScanRequest(BaseModel):
    name: str
    target_url: str

    @field_validator("target_url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("target_url must not be empty")
        if v.startswith("-"):
            raise ValueError("target_url must not start with '-'")
        if any(ch.isspace() or ord(ch) < 0x20 for ch in v):
            raise ValueError("target_url must not contain whitespace or control characters")
        parsed = urlparse(v)
        scheme = (parsed.scheme or "").lower()
        if scheme not in _ALLOWED_GIT_SCHEMES:
            raise ValueError(
                f"Unsupported URL scheme '{parsed.scheme}'. "
                f"Allowed: {', '.join(_ALLOWED_GIT_SCHEMES)}"
            )
        if not parsed.hostname or not _HOST_RE.match(parsed.hostname):
            raise ValueError("target_url must include a valid hostname")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        if len(v) > 255:
            raise ValueError("name must be at most 255 characters")
        return v


# DAST profiles. `passive` is spider + passive analysis only — never sends
# attack payloads. `active` adds the active scanner (real XSS/SQLi/etc probes)
# and is gated on a higher privilege at the router layer.
DastProfile = Literal["passive", "active"]

# How ZAP discovers endpoints before the passive/active stages run.
#   • spider        — classic HTTP crawler. Good for server-rendered sites,
#                     fast, finds <a> and <form>. Misses anything generated
#                     by JavaScript.
#   • ajax_spider   — headless browser walks the SPA, clicks elements, follows
#                     XHR. Mandatory for React/Vue/Angular apps; ~5x slower.
#   • openapi       — imports an OpenAPI/Swagger spec from a URL. Best for
#                     REST APIs — gives full coverage without any crawl.
DastDiscoveryMode = Literal["spider", "ajax_spider", "openapi"]


# Practical caps for the exclude list. Big enough for any realistic use case,
# tight enough that a buggy/abusive client can't blow up the JSON column.
_MAX_EXCLUDES = 20
_MAX_EXCLUDE_LEN = 256


# Authentication options for the DAST scanner.
#
# Credentials are deliberately NOT persisted in the database — they are passed
# to the Celery task as arguments (broker message in Redis) and discarded
# after the worker consumes the task. The visible `extra.auth_type` on the
# ScanJob is just a label for the UI; the actual token/password never round-
# trips through any API response.
#
# Four methods supported:
#   • bearer    — adds `Authorization: Bearer <token>` to every ZAP request via
#                 the Replacer add-on. Works for JWT/session-token APIs that
#                 accept the header.
#   • cookie    — adds `Cookie: <raw value>` to every ZAP request via Replacer.
#                 Use when the app stores session in httpOnly cookies that the
#                 user pulls from their browser DevTools.
#   • form      — ZAP performs a form-encoded login itself (POST
#                 `username=…&password=…`), then carries the resulting session
#                 through subsequent requests via cookies. Classic web forms.
#   • json_form — like `form`, but ZAP POSTs a JSON body to the login URL.
#                 Used by FastAPI/Express-style backends whose login endpoint
#                 expects `{"email": "...", "password": "..."}` rather than
#                 form-encoded data.
AuthType = Literal["bearer", "cookie", "form", "json_form"]


class AuthConfig(BaseModel):
    type: AuthType
    # bearer
    token: Optional[str] = None
    # cookie — raw value of the Cookie header, e.g. "access_token=ey...; ..."
    cookie: Optional[str] = None
    # form / json_form
    login_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    # Field names for form-encoded login (used only when type=="form").
    # `json_form` ignores these and uses body_template instead.
    username_field: str = "username"
    password_field: str = "password"
    # Raw JSON template the user wants posted as the login request body.
    # Required for type=="json_form". Must contain the literal placeholders
    # {%username%} and {%password%} — ZAP substitutes them with the values
    # of `username` / `password` at scan time.
    #
    # Why a free-form template instead of two key fields? Many real login
    # endpoints need more than just user+pass — client_id, device fingerprint,
    # `remember_me`, nested envelopes etc. A textarea covers all of them
    # without growing the schema every time a new field is needed.
    #
    # Example for FastAPI:
    #   {"email":"{%username%}","password":"{%password%}"}
    body_template: Optional[str] = None
    # Optional regex ZAP uses to detect a "logged in" response — if present
    # in the body, the session is considered active; if absent, ZAP re-auths.
    logged_in_regex: Optional[str] = None

    @field_validator("token", "cookie", "login_url", "username", "password",
                     "username_field", "password_field", "body_template",
                     "logged_in_regex")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @model_validator(mode="after")
    def check_consistency(self):
        # Per-type requirements. Validators on individual fields can't see
        # cross-field state, so the "you forgot the token" check lives here.
        if self.type == "bearer":
            if not self.token:
                raise ValueError("bearer auth requires `token`")
            if len(self.token) > 8192:
                raise ValueError("bearer token is implausibly long (>8 KiB)")
        elif self.type == "cookie":
            if not self.cookie:
                raise ValueError("cookie auth requires `cookie`")
            if len(self.cookie) > 8192:
                raise ValueError("cookie value is implausibly long (>8 KiB)")
            # Reject obvious garbage — Cookie header values cannot contain
            # newlines (header smuggling) or control chars.
            if any(ord(ch) < 0x20 for ch in self.cookie):
                raise ValueError("cookie must not contain control characters or newlines")
        elif self.type in ("form", "json_form"):
            missing = [
                f for f, v in [
                    ("login_url", self.login_url),
                    ("username", self.username),
                    ("password", self.password),
                ] if not v
            ]
            if missing:
                raise ValueError(f"{self.type} auth requires: {', '.join(missing)}")
            _validate_web_url(self.login_url, field_name="login_url")
            if self.type == "json_form":
                _validate_json_body_template(self.body_template)
        return self


class SubmitWebScanRequest(BaseModel):
    name: str
    target_url: str
    profile: DastProfile = "passive"
    discovery_mode: DastDiscoveryMode = "spider"
    # Required when discovery_mode == "openapi". Spec is fetched by ZAP, not
    # us — same scheme rules apply (http/https, not localhost).
    openapi_url: Optional[str] = None
    # Path patterns to keep out of scope. Two forms accepted by the worker:
    #   • plain path / glob — "/logout", "/admin/*", "/users/me/delete"
    #     → expanded to a regex anchored on the target host
    #   • full regex — anything not starting with "/" is passed through as-is
    # The runner converts these to ZAP's excludeFromContext patterns. Empty
    # list = no exclusions (everything on host is in scope).
    exclude_paths: list[str] = []
    # Optional. Credentials never reach the database — see AuthConfig docs.
    auth: Optional[AuthConfig] = None

    @field_validator("target_url")
    @classmethod
    def url_ok(cls, v: str) -> str:
        return _validate_web_url(v, field_name="target_url")

    @field_validator("openapi_url")
    @classmethod
    def openapi_ok(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        return _validate_web_url(v, field_name="openapi_url")

    @field_validator("exclude_paths")
    @classmethod
    def excludes_ok(cls, v: list[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in v or []:
            s = (raw or "").strip()
            if not s:
                continue
            if any(ch.isspace() or ord(ch) < 0x20 for ch in s):
                raise ValueError("exclude_paths entries must not contain whitespace or control characters")
            if len(s) > _MAX_EXCLUDE_LEN:
                raise ValueError(f"exclude_paths entry too long (>{_MAX_EXCLUDE_LEN} chars)")
            cleaned.append(s)
        if len(cleaned) > _MAX_EXCLUDES:
            raise ValueError(f"At most {_MAX_EXCLUDES} exclude_paths allowed")
        return cleaned

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        if len(v) > 255:
            raise ValueError("name must be at most 255 characters")
        return v

    @model_validator(mode="after")
    def check_openapi_consistency(self):
        # Cross-field rule: openapi mode requires the spec URL, and providing
        # an openapi URL while in a crawl mode is almost always a mistake — be
        # strict so the user notices instead of silently ignoring the field.
        if self.discovery_mode == "openapi" and not self.openapi_url:
            raise ValueError("openapi_url is required when discovery_mode is 'openapi'")
        if self.discovery_mode != "openapi" and self.openapi_url:
            raise ValueError(
                "openapi_url can only be set when discovery_mode is 'openapi'"
            )
        return self


def _validate_json_body_template(v: Optional[str]) -> None:
    """
    Validate a json_form body template:
      • must be present
      • must contain both {%username%} and {%password%} placeholders
      • must parse as JSON once placeholders are replaced with safe stand-ins

    The placeholder check matters because ZAP only substitutes those two
    exact strings — typos like `{% username %}` or `{{username}}` will be
    sent verbatim to the login endpoint and silently fail auth.
    """
    import json as _json
    if not v or not v.strip():
        raise ValueError("json_form auth requires `body_template`")
    if len(v) > 16384:
        raise ValueError("body_template is implausibly long (>16 KiB)")
    if "{%username%}" not in v:
        raise ValueError("body_template must contain the literal `{%username%}` placeholder")
    if "{%password%}" not in v:
        raise ValueError("body_template must contain the literal `{%password%}` placeholder")
    # Substitute placeholders with dummy strings and try to parse — catches
    # quoting/comma mistakes before the worker hits ZAP with a broken body.
    probe = v.replace("{%username%}", "u").replace("{%password%}", "p")
    try:
        _json.loads(probe)
    except _json.JSONDecodeError as exc:
        raise ValueError(f"body_template is not valid JSON: {exc.msg} at line {exc.lineno} col {exc.colno}")


def _validate_web_url(v: str, *, field_name: str) -> str:
    """
    Shared URL validation for both `target_url` and `openapi_url`. Same scheme
    + private-IP rules apply to both — if we let the user point `openapi_url`
    at `http://169.254.169.254/` we'd be re-opening the SSRF door we just
    closed for `target_url`.
    """
    v = v.strip()
    if not v:
        raise ValueError(f"{field_name} must not be empty")
    if v.startswith("-"):
        raise ValueError(f"{field_name} must not start with '-'")
    if any(ch.isspace() or ord(ch) < 0x20 for ch in v):
        raise ValueError(f"{field_name} must not contain whitespace or control characters")
    parsed = urlparse(v)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_WEB_SCHEMES:
        raise ValueError(
            f"Unsupported URL scheme '{parsed.scheme}'. "
            f"Allowed: {', '.join(_ALLOWED_WEB_SCHEMES)}"
        )
    host = parsed.hostname or ""
    if not host or not _HOST_RE.match(host):
        raise ValueError(f"{field_name} must include a valid hostname")
    if _is_private_or_local(host):
        raise ValueError(
            "Cannot scan private, loopback, or link-local addresses. "
            "Use a publicly reachable URL."
        )
    return v


# ── Response schemas ───────────────────────────────────────────────────────────

class ScanFindingOut(BaseModel):
    id: str
    tool: str
    rule_id: str
    severity: str
    confidence: Optional[str]
    title: str
    message: str
    file_path: str
    line_start: Optional[int]
    line_end: Optional[int]
    code_snippet: Optional[str]
    cwe: Optional[str]
    owasp: Optional[str]
    fingerprint: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanJobOut(BaseModel):
    id: str
    organization_id: str
    created_by: str
    name: str
    scan_type: str
    status: str
    target_type: str
    target_url: Optional[str]
    target_path: Optional[str] = None
    celery_task_id: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    findings_count: int
    extra: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScanJobDetailOut(ScanJobOut):
    # NOTE: previously this declared `findings: list[ScanFindingOut] = []`,
    # which made Pydantic with `from_attributes=True` access `job.findings`
    # and trigger SQLAlchemy lazy-loading of every finding on each detail
    # request. The dashboard polls this endpoint every 3 s while a scan is
    # active and never uses the embedded list (it calls /findings separately),
    # so loading thousands of rows per poll was pure waste. The detail view
    # is now identical to the list view — clients should hit /findings.
    model_config = {"from_attributes": True}


class ScanJobListOut(BaseModel):
    total: int
    items: list[ScanJobOut]


class ScanStatusCountsOut(BaseModel):
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total: int = 0


class FindingsListOut(BaseModel):
    total: int
    items: list[ScanFindingOut]
    severity_counts: dict[str, int]
    # True when len(items) < total — UI uses this to show a "results truncated"
    # banner instead of silently misrepresenting per-tool counts.
    truncated: bool = False


# ── Org-level summary (dashboard overview) ─────────────────────────────────────

class RecentScanSummary(BaseModel):
    """Lightweight scan row used in the org dashboard activity feed."""
    id: str
    name: str
    scan_type: str
    status: str
    target_type: Optional[str] = None
    target_url: Optional[str] = None
    findings_count: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrgSummaryOut(BaseModel):
    """
    Single-round-trip payload for the org dashboard overview tab.

    severity_counts  — aggregate across ALL scan findings for this org
                       (not limited to a single job).
    total_findings   — sum of severity_counts values.
    status_counts    — live scan status breakdown (same as /scans/stats).
    recent_scans     — the 8 most-recently created jobs, newest first.
    """
    severity_counts: dict[str, int]
    total_findings: int
    status_counts: dict[str, int]
    recent_scans: list[RecentScanSummary]
