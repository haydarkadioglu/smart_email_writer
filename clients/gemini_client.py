from typing import Optional, Dict, Any
import textwrap
import os

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - optional at runtime
    genai = None
    types = None

from models.email_models import GeneratedEmail
from config.app_config import GEMINI_MODEL


class GeminiClient:
    def __init__(self, api_key: str = "", model_name: str = GEMINI_MODEL) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self._configured = False
        self._client = None
        if api_key and genai is not None:
            try:
                self._client = genai.Client(api_key=api_key)
                self._configured = True
            except Exception:
                self._configured = False

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
        if not purpose:
            purpose = "General correspondence"

        profile_text = ""
        if profile:
            # Include all profile fields for comprehensive context
            name = profile.get("name")
            title = profile.get("title")
            company = profile.get("company")
            experience = profile.get("experience")
            location = profile.get("location")
            phone = profile.get("phone")
            email = profile.get("email")
            website = profile.get("website")
            linkedin = profile.get("linkedin")
            github = profile.get("github")
            skills = profile.get("skills")
            summary = profile.get("summary")
            achievements = profile.get("achievements")
            
            extras = []
            if name:
                extras.append(f"Name: {name}")
            if title:
                extras.append(f"Title: {title}")
            if company:
                extras.append(f"Company: {company}")
            if experience:
                extras.append(f"Experience: {experience}")
            if location:
                extras.append(f"Location: {location}")
            if phone:
                extras.append(f"Phone: {phone}")
            if email:
                extras.append(f"Email: {email}")
            if website:
                extras.append(f"Website: {website}")
            if linkedin:
                extras.append(f"LinkedIn: {linkedin}")
            if github:
                extras.append(f"GitHub: {github}")
            if skills:
                extras.append(f"Skills: {skills}")
            if summary:
                extras.append(f"Summary: {summary}")
            if achievements:
                extras.append(f"Achievements: {achievements}")
            
            if extras:
                profile_text = "\n".join(extras)

        if not self._configured:
            subject = f"Regarding: {purpose}"
            body_lines = [
                f"Merhaba {recipient_name or 'Alıcı'},",
                "",
                f"{purpose} hakkında iletişime geçmek isterim.",
            ]
            if additional_context:
                body_lines.append(additional_context)
            if profile_text:
                body_lines += ["", "Hakkımda:", profile_text]
            body_lines += ["", "Saygılarımla,", ""]
            return GeneratedEmail(subject=subject, body="\n".join(body_lines).strip())

        # Improved prompt for better email generation
        prompt = textwrap.dedent(
            f"""
            You are a professional email writing assistant. Create a well-structured, {tone.lower()} email in {language}.

            TASK: Write a complete email based on the following information:

            PURPOSE/TOPIC: {purpose}
            RECIPIENT: {recipient_name}
            ADDITIONAL CONTEXT: {additional_context}
            AUTHOR PROFILE: {profile_text}
            EMAIL LENGTH: {email_length}

            REQUIREMENTS:
            - Write a professional email that addresses the purpose/topic
            - If this appears to be a job application, write a compelling cover letter
            - Use the author profile to personalize the email appropriately
            - Keep the tone {tone.lower()} and language {language}
            - Make it engaging and relevant to the recipient
            - Include proper greeting and closing
            - Follow the specified email length: {email_length}
            - For "Very Short": write only 1 concise paragraph but still include greeting and closing 
            - Do NOT repeat the instructions or context verbatim
            - Use the profile information naturally in the email content

            Return ONLY a JSON object with these exact keys:
            {{
                "subject": "Clear, professional subject line",
                "body": "Complete email body with proper formatting"
            }}
            """
        ).strip()

        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            generate_content_config = types.GenerateContentConfig()

            # Collect all chunks
            full_text = ""
            for chunk in self._client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=generate_content_config,
            ):
                full_text += chunk.text or ""

            import json, re
            match = re.search(r"\{[\s\S]*\}", full_text)
            if match:
                data = json.loads(match.group(0))
                subject = data.get("subject") or f"Regarding: {purpose}"
                body = data.get("body") or ""
            else:
                lines = [l.strip() for l in full_text.splitlines() if l.strip()]
                subject = lines[0][:120] if lines else f"Regarding: {purpose}"
                body = "\n".join(lines[1:]) if len(lines) > 1 else full_text
            return GeneratedEmail(subject=subject, body=body.strip())
        except Exception:
            subject = f"Regarding: {purpose}"
            body_lines = [
                f"Merhaba {recipient_name or 'Alıcı'},",
                "",
                f"{purpose} hakkında iletişime geçmek isterim.",
            ]
            if additional_context:
                body_lines.append(additional_context)
            if profile_text:
                body_lines += ["", "Hakkımda:", profile_text]
            body_lines += ["", "Saygılarımla,", ""]
            return GeneratedEmail(subject=subject, body="\n".join(body_lines).strip())
