"""Async SMTP email service with structured send/fail logging."""

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable

import anyio

from core.config import settings

logger = logging.getLogger("progressionx.email")


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    mime_type: str = "application/octet-stream"


class EmailService:
    """Thin SMTP wrapper. Runs blocking smtplib in a worker thread so it
    plays nicely with FastAPI async routes and BackgroundTasks."""

    def __init__(self) -> None:
        self._configured = bool(
            settings.SMTP_HOST and settings.SMTP_FROM
        )

    @property
    def configured(self) -> bool:
        return self._configured

    async def send(
        self,
        *,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        attachments: Iterable[EmailAttachment] | None = None,
        context: str = "email",
    ) -> bool:
        """Send an email. Returns True on success, False on failure.

        Never raises — this is meant to be called from background tasks where
        unhandled exceptions would be swallowed silently. All outcomes are
        logged with a `context` label so they can be filtered in logs.
        """
        if not self._configured:
            logger.error(
                "email.send.skipped context=%s to=%s reason=smtp_not_configured",
                context,
                to,
            )
            return False

        msg = EmailMessage()
        msg["From"] = (
            f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
            if settings.SMTP_FROM_NAME
            else settings.SMTP_FROM
        )
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")

        for att in attachments or []:
            maintype, _, subtype = att.mime_type.partition("/")
            if not subtype:
                maintype, subtype = "application", "octet-stream"
            msg.add_attachment(
                att.content,
                maintype=maintype,
                subtype=subtype,
                filename=att.filename,
            )

        try:
            await anyio.to_thread.run_sync(self._send_sync, msg)
            logger.info(
                "email.send.ok context=%s to=%s subject=%r attachments=%d",
                context,
                to,
                subject,
                len(list(attachments or [])),
            )
            return True
        except Exception as exc:
            logger.error(
                "email.send.fail context=%s to=%s subject=%r error=%s: %s",
                context,
                to,
                subject,
                type(exc).__name__,
                exc,
            )
            return False

    def _send_sync(self, msg: EmailMessage) -> None:
        host = settings.SMTP_HOST
        port = settings.SMTP_PORT
        user = settings.SMTP_USER
        password = settings.SMTP_PASSWORD
        use_tls = settings.SMTP_USE_TLS

        if port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
            return

        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            if use_tls:
                ctx = ssl.create_default_context()
                smtp.starttls(context=ctx)
                smtp.ehlo()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)


email_service = EmailService()
