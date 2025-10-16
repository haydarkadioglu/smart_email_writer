from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Provider(Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"


@dataclass
class Attachment:
    filename: str
    content: bytes
    mime_type: str


@dataclass
class EmailRequest:
    provider: Provider
    sender_email: str
    sender_password: str
    recipient_email: str
    subject: str
    body: str
    attachments: Optional[List[Attachment]] = None


@dataclass
class GeneratedEmail:
    subject: str
    body: str
