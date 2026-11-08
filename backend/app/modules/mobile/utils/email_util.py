import asyncio
from email.message import EmailMessage
import smtplib
from app.core.config import settings


def _send_email_sync(subject: str, to: str, body: str) -> None:
    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    user = settings.SMTP_USER
    password = settings.SMTP_PASS
    from_email = settings.FROM_EMAIL or user

    if not host or not user or not password:
        raise RuntimeError("SMTP not configured (SMTP_HOST/SMTP_USER/SMTP_PASS)")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)


async def send_email(subject: str, to: str, body: str) -> None:
    """Gửi email bất đồng bộ qua thread pool để không block event loop."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _send_email_sync, subject, to, body)

