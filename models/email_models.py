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


@dataclass
class RecipientData:
    name: str
    email: str
    description: str
    custom_fields: dict = None


@dataclass
class BulkEmailRequest:
    provider: Provider
    sender_email: str
    sender_password: str
    subject: str
    body_template: str
    recipients: List[RecipientData]
    attachments: Optional[List[Attachment]] = None
    use_ai_generation: bool = False
    ai_purpose: str = ""
    ai_tone: str = "Professional"
    ai_language: str = "English"
    ai_length: str = "Medium (3-4 paragraphs)"
    ai_additional_context: str = ""