from typing import Tuple
import traceback

from models.email_models import EmailRequest, Provider
from clients.gmail_client import GmailClient
from clients.outlook_client import OutlookClient


class EmailSender:
    def __init__(self) -> None:
        self.gmail = GmailClient()
        self.outlook = OutlookClient()

    def send(self, request: EmailRequest) -> Tuple[bool, str]:
        try:
            if request.provider == Provider.GMAIL:
                self.gmail.send(
                    sender_email=request.sender_email,
                    sender_password=request.sender_password,
                    recipient_email=request.recipient_email,
                    subject=request.subject,
                    body=request.body,
                    attachments=request.attachments,
                )
            elif request.provider == Provider.OUTLOOK:
                self.outlook.send(
                    sender_email=request.sender_email,
                    sender_password=request.sender_password,
                    recipient_email=request.recipient_email,
                    subject=request.subject,
                    body=request.body,
                    attachments=request.attachments,
                )
            else:
                return False, "Unsupported provider"
            return True, ""
        except Exception as e:
            details = traceback.format_exc()
            return False, f"{e.__class__.__name__}: {e}\n{details}"
