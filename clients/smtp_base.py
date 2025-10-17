import smtplib
import ssl
from abc import ABC, abstractmethod
from email.message import EmailMessage
from email.header import Header
from email.policy import SMTPUTF8
from email.headerregistry import Address
from typing import List, Optional, Tuple

from models.email_models import Attachment


def _split_email(email_addr: str) -> Tuple[str, str]:
    if not email_addr or "@" not in email_addr:
        return email_addr, ""
    local, domain = email_addr.split("@", 1)
    try:
        domain_idna = domain.encode("idna").decode("ascii")
    except Exception:
        domain_idna = domain
    return local, domain_idna


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
        msg = EmailMessage(policy=SMTPUTF8)
        # RFC-compliant addresses (IDNA domain)
        s_local, s_domain = _split_email(sender_email)
        r_local, r_domain = _split_email(recipient_email)
        msg["From"] = str(Address(username=s_local, domain=s_domain)) if s_domain else sender_email
        msg["To"] = str(Address(username=r_local, domain=r_domain)) if r_domain else recipient_email
        # Encode subject safely for non-ASCII (cast Header to str)
        msg["Subject"] = str(Header(subject or "", "utf-8"))
        # UTF-8 body
        msg.set_content(body or "", subtype="plain", charset="utf-8")
        if attachments:
            for att in attachments:
                maintype, subtype = (att.mime_type.split("/", 1) if "/" in att.mime_type else ("application", "octet-stream"))
                # RFC2231-encoded filename for non-ASCII
                filename_param = ("utf-8", "", att.filename)
                msg.add_attachment(att.content, maintype=maintype, subtype=subtype, filename=filename_param)
        return msg

    @staticmethod
    def _send_starttls(host: str, port: int, username: str, password: str, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            mail_opts = ["SMTPUTF8"] if server.has_extn("smtputf8") else []
            server.send_message(message, mail_options=mail_opts)

    @staticmethod
    def _send_ssl(host: str, port: int, username: str, password: str, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(username, password)
            mail_opts = ["SMTPUTF8"] if server.has_extn("smtputf8") else []
            server.send_message(message, mail_options=mail_opts)
