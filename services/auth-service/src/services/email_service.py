import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

SMTP_HOST      = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT      = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER      = os.getenv("SMTP_USER", "OmniSecura@gmail.com")
SMTP_PASSWORD  = os.getenv("SMTP_PASSWORD", "czfzmqtwcbqedmwh")
MAIL_FROM      = os.getenv("MAIL_FROM", SMTP_USER)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "CyberCore")
APP_URL        = os.getenv("APP_URL", "http://localhost:8000")

# Templates live at:  src/templates/emails/
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"

# ── Jinja2 ────────────────────────────────────────────────────────────────────

_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _render(template_name: str, **context) -> str:
    return _jinja.get_template(template_name).render(
        app_url=APP_URL,
        app_name=MAIL_FROM_NAME,
        **context,
    )


def _send(to: str, subject: str, html: str) -> None:
    """Open one SMTP connection, send, close. Raises on any failure."""
    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError("SMTP_USER and SMTP_PASSWORD must be set in env.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(MAIL_FROM, to, msg.as_string())

    logger.info("Email sent | to=%s subject=%r", to, subject)


# ── Public API ────────────────────────────────────────────────────────────────

class EmailService:
    """
    Renders Jinja2 templates and sends emails over SMTP.

    Token generation and persistence are NOT this service's responsibility.
    The caller (user_service) generates the token, stores its SHA-256 hash
    in user_tokens, and passes the plaintext token here for embedding in the link.
    """

    def send_verify_email(self, to: str, full_name: str, token: str) -> None:
        """Send email-verification link. Token expires in 24 h."""
        html = _render(
            "verify_email.html",
            full_name=full_name,
            verify_url=f"{APP_URL}/verify-email?token={token}",
        )
        _send(to, subject=f"Verify your {MAIL_FROM_NAME} email address", html=html)

    def send_reset_password(self, to: str, full_name: str, token: str) -> None:
        """Send password-reset link. Token expires in 1 h."""
        html = _render(
            "reset_password.html",
            full_name=full_name,
            reset_url=f"{APP_URL}/reset-password?token={token}",
        )
        _send(to, subject=f"Reset your {MAIL_FROM_NAME} password", html=html)

    def send_org_invite(
        self,
        to: str,
        invited_by_name: str,
        org_name: str,
        role: str,
        token: str,
    ) -> None:
        """Send org-invitation link. Token expires in 48 h."""
        html = _render(
            "org_invite.html",
            invited_by_name=invited_by_name,
            org_name=org_name,
            role=role,
            invite_url=f"{APP_URL}/invite?token={token}",
        )
        _send(to, subject=f"You've been invited to {org_name} on {MAIL_FROM_NAME}", html=html)

    def send_welcome(self, to: str, full_name: str) -> None:
        """Send welcome email immediately after registration. No token."""
        html = _render("welcome.html", full_name=full_name)
        _send(to, subject=f"Welcome to {MAIL_FROM_NAME}!", html=html)