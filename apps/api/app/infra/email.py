import logging

import aiosmtplib

from app.core.config import get_settings
from app.domain.ports import IEmailSender

logger = logging.getLogger(__name__)


class EmailSender(IEmailSender):
    async def enviar_recuperacion(self, correo: str, enlace: str) -> None:
        settings = get_settings()
        if not settings.smtp_host:
            logger.info("SMTP no configurado; recuperación omitida para %s", correo)
            return

        asunto = "Recuperación de contraseña"
        cuerpo = (
            "Recibimos una solicitud para restablecer tu contraseña.\n\n"
            f"Usá este enlace: {enlace}\n\n"
            "Si no solicitaste este cambio, ignorá este correo."
        )

        mensaje = (
            f"From: {settings.smtp_from}\r\n"
            f"To: {correo}\r\n"
            f"Subject: {asunto}\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "\r\n"
            f"{cuerpo}"
        )

        await aiosmtplib.send(
            mensaje,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_port == 587,
        )
