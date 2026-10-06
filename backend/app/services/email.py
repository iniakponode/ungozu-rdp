"""Async SMTP email service suitable for production SMTP or local Mailpit."""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib
from app.core.config import settings
logger = logging.getLogger(__name__)

async def send_email(to: str, subject: str, html_body: str, *, plain_body: str | None = None, attachments: list[tuple[str, bytes, str]] | None = None) -> bool:
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured - skipping email to %s", to)
        return False
    msg = MIMEMultipart("mixed")
    msg["From"] = settings.smtp_from_address or "no-reply@rdp.local"
    msg["To"] = to
    msg["Subject"] = subject
    alt = MIMEMultipart("alternative")
    if plain_body: alt.attach(MIMEText(plain_body, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8")); msg.attach(alt)
    if attachments:
        for filename, data, mime in attachments:
            maintype, subtype = mime.split("/", 1) if "/" in mime else ("application", "octet-stream")
            part = MIMEBase(maintype, subtype); part.set_payload(data); encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=filename); msg.attach(part)
    try:
        kwargs = dict(hostname=settings.SMTP_HOST, port=settings.SMTP_PORT, use_tls=settings.SMTP_USE_TLS)
        if settings.SMTP_USER:
            kwargs.update(username=settings.SMTP_USER, password=settings.SMTP_PASS)
        await aiosmtplib.send(msg, **kwargs)
        logger.info("Email sent to %s: %s", to, subject); return True
    except Exception:
        logger.exception("Failed to send email to %s", to); return False
