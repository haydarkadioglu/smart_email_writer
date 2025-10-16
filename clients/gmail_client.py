from typing import List, Optional

from models.email_models import Attachment
from .smtp_base import SmtpClient


class GmailClient(SmtpClient):
    HOST = "smtp.gmail.com"
    PORT_TLS = 587

    def send(
        self,
        sender_email: str,
        sender_password: str,
        recipient_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[Attachment]] = None,
    ) -> None:
        message = self._build_message(sender_email, recipient_email, subject, body, attachments)
        # Gmail supports STARTTLS on 587
        self._send_starttls(self.HOST, self.PORT_TLS, sender_email, sender_password, message)
