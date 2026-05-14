import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

SMTP_HOST      = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT      = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER      = os.getenv("SMTP_USER", "")
SMTP_PASSWORD  = os.getenv("SMTP_PASSWORD", "")
MAIL_FROM      = os.getenv("MAIL_FROM", SMTP_USER)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "CyberCore")
APP_URL        = os.getenv("APP_URL", "http://localhost")

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"

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


class OrgEmailClient:
    def send_org_invite(
        self,
        to: str,
        invited_by_name: str,
        org_name: str,
        role: str,
        token: str,
    ) -> None:
        html = _render(
            "org_invite.html",
            invited_by_name=invited_by_name,
            org_name=org_name,
            role=role,
            invite_url=f"{APP_URL}/invite?token={token}",
        )
        _send(to, subject=f"You've been invited to {org_name} on {MAIL_FROM_NAME}", html=html)

    def send_ownership_transfer(
        self,
        to: str,
        from_owner_name: str,
        org_name: str,
        token: str,
    ) -> None:
        html = _render(
            "ownership_transfer.html",
            from_owner_name=from_owner_name,
            org_name=org_name,
            transfer_url=f"{APP_URL}/transfer-ownership/accept?token={token}",
        )
        _send(to, subject=f"You've been offered ownership of {org_name} on {MAIL_FROM_NAME}", html=html)
