import smtplib
import ssl
from abc import ABC, abstractmethod
from email.message import EmailMessage
from typing import List, Optional

from models.email_models import Attachment


class SmtpClient(ABC):
    @abstractmethod
    def send(
        self,
        sender_email: str,
        sender_password: str,
        recipient_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[Attachment]] = None,
    ) -> None:
        raise NotImplementedError

    @staticmethod
    def _build_message(
        sender_email: str,
        recipient_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[Attachment]] = None,
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.set_content(body)
        if attachments:
            for att in attachments:
                maintype, subtype = (att.mime_type.split("/", 1) if "/" in att.mime_type else ("application", "octet-stream"))
                msg.add_attachment(att.content, maintype=maintype, subtype=subtype, filename=att.filename)
        return msg

    @staticmethod
    def _send_starttls(host: str, port: int, username: str, password: str, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.send_message(message)

    @staticmethod
    def _send_ssl(host: str, port: int, username: str, password: str, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(username, password)
            server.send_message(message)
