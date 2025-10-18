import os
import json
import textwrap
from typing import Optional, Dict, Any

from models.email_models import GeneratedEmail
from config.app_config import GROQ_MODEL

try:
    from groq import Groq  # type: ignore
except Exception:
    Groq = None


class GroqClient:
    def __init__(self, api_key: str = "", model_name: str = GROQ_MODEL) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model_name = model_name
        self._client = None
        self._configured = False
        self._init_error: Optional[Exception] = None
        try:
            if Groq is None:
                raise ImportError("groq Python package not installed. Install with: pip install groq")
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is missing or empty. Add it to your .env and restart the app")
            self._client = Groq(api_key=self.api_key)
            self._configured = True
        except Exception as e:
            self._init_error = e
            self._configured = False

    def _not_configured_message(self) -> str:
        if isinstance(self._init_error, ImportError):
            return str(self._init_error)
        if isinstance(self._init_error, ValueError):
            return str(self._init_error)
        return f"Groq client failed to initialize: {self._init_error}"

    def generate_email(
        self,
        purpose: str,
        recipient_name: str,
        tone: str = "Professional",
        language: str = "Turkish",
        additional_context: str = "",
        profile: Optional[Dict[str, Any]] = None,
        email_length: str = "Medium (3-4 paragraphs)",
    ) -> GeneratedEmail:
        if not self._configured:
            raise RuntimeError(self._not_configured_message())

        if not purpose:
            purpose = "General correspondence"

        profile_text = ""
        if profile:
            # Flatten profile to readable lines
            lines = []
            for k, v in profile.items():
                if v:
                    lines.append(f"{k.capitalize()}: {v}")
            profile_text = "\n".join(lines)

        system_prompt = textwrap.dedent(
            f"""
            You are a professional email writing assistant. Create a well-structured, {tone.lower()} email in {language}.
            TASK: Write a complete email using the inputs provided.
            REQUIREMENTS:
            - Address the purpose/topic
            - If this appears to be a job application, write a compelling cover letter
            - Personalize using the author's profile
            - Follow the specified length: {email_length}
            - For "Very Short": write only 1 concise paragraph but still include greeting and closing, make line breaks and also add the links

            - Include greeting and closing
            - Return ONLY JSON with keys subject, body.
            """
        ).strip()

        user_prompt = textwrap.dedent(
            f"""
            PURPOSE/TOPIC: {purpose}
            RECIPIENT: {recipient_name}
            ADDITIONAL CONTEXT: {additional_context}
            AUTHOR PROFILE:\n{profile_text}
            """
        ).strip()

        try:
            chat = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                stream=False,
            )
            text = chat.choices[0].message.content if chat and chat.choices else ""
            match = None
            try:
                match = json.loads(text)
            except Exception:
                pass
            if isinstance(match, dict):
                subject = match.get("subject") or f"Regarding: {purpose}"
                body = match.get("body") or text
                return GeneratedEmail(subject=subject, body=(body or "").strip())
            # Fallback heuristic
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            subject = lines[0][:120] if lines else f"Regarding: {purpose}"
            body = "\n".join(lines[1:]) if len(lines) > 1 else text
            return GeneratedEmail(subject=subject, body=(body or "").strip())
        except Exception as e:
            # Surface upstream errors (e.g., 401, 404) for easier debugging in UI
            raise RuntimeError(f"Groq generation failed: {e}")
