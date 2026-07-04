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

    def _call_raw(self, prompt: str) -> str:
        """Send a raw prompt and return the text response verbatim."""
        if not self._configured or self._client is None:
            raise RuntimeError("Gemini client is not configured. Check your GEMINI_API_KEY.")
        full_text = ""
        for chunk in self._client.models.generate_content_stream(
            model=self.model_name,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(),
        ):
            full_text += chunk.text or ""
        return full_text

    def _call_raw_stream(self, prompt: str, chunk_cb=None) -> str:
        """Stream a raw prompt; calls chunk_cb(text) for each chunk. Returns full text."""
        if not self._configured or self._client is None:
            raise RuntimeError("Gemini client is not configured. Check your GEMINI_API_KEY.")
        full_text = ""
        for chunk in self._client.models.generate_content_stream(
            model=self.model_name,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(),
        ):
            text = chunk.text or ""
            full_text += text
            if text and chunk_cb:
                chunk_cb(text)
        return full_text

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
            extras = []
            friendly_names = {
                "name": "Name",
                "email": "Email",
                "company": "Company",
                "role": "Role/Title",
                "website": "Website",
                "signature": "Email Signature",
                "about_me": "About Me / General Info",
                "experience": "Experience",
                "location": "Location",
                "phone": "Phone",
                "linkedin": "LinkedIn",
                "github": "GitHub",
                "skills": "Skills",
                "summary": "Summary",
                "achievements": "Achievements"
            }
            for k, v in profile.items():
                if v:
                    label = friendly_names.get(k, k.replace("_", " ").title())
                    extras.append(f"{label}: {v}")
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
            - Follow the specified email length strictly:
              * "Very Short (1 paragraph)": The email body must have EXACTLY this structure (each part on its OWN line, separated by a blank line):
                  Greeting line (e.g. Dear ...),
                  [blank line]
                  ONE short paragraph (2-3 sentences max) covering the purpose,
                  [blank line]
                  Closing line (e.g. Best regards, / Sincerely,) + sender name.
                  Do NOT merge the greeting, body, and closing into a single block of text.
              * "Short (1-2 paragraphs)": greeting + 1-2 short paragraphs + closing, all on separate lines.
              * "Medium (3-4 paragraphs)": standard multi-paragraph email.
              * "Long (5+ paragraphs)": detailed email.
            - Do NOT repeat the instructions or context verbatim
            - Use the profile information naturally in the email content
            - ATTACHMENTS RULE: Only reference files that are explicitly mentioned as attached in the context/prompt (e.g., in ADDITIONAL CONTEXT or user files). If only a CV/resume is attached, do NOT write "including my CV and academic certificates / references / transcripts / cover letter". ONLY mention the CV. Never assume or hallucinate attachments that were not uploaded by the user.
            - LINKS/WEBSITES RULE: If the author's profile contains a Website, GitHub, or LinkedIn, and the email is an application, cover letter, or introductory email, you MUST naturally include these links in the body (e.g., "My portfolio is available at [Website]" or "You can find my projects at [GitHub]"). Do not omit them.

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

    def refine_email(
        self,
        subject: str,
        body: str,
        instruction: str,
        tone: str = "Professional",
        language: str = "Turkish",
        profile: Optional[Dict[str, Any]] = None,
    ) -> GeneratedEmail:
        if not instruction:
            return GeneratedEmail(subject=subject, body=body)

        profile_text = ""
        if profile:
            extras = []
            friendly_names = {
                "name": "Name",
                "email": "Email",
                "company": "Company",
                "role": "Role/Title",
                "website": "Website",
                "signature": "Email Signature",
                "about_me": "About Me / General Info",
                "experience": "Experience",
                "location": "Location",
                "phone": "Phone",
                "linkedin": "LinkedIn",
                "github": "GitHub",
                "skills": "Skills",
                "summary": "Summary",
                "achievements": "Achievements"
            }
            for k, v in profile.items():
                if v:
                    label = friendly_names.get(k, k.replace("_", " ").title())
                    extras.append(f"{label}: {v}")
            if extras:
                profile_text = "\n".join(extras)

        if not self._configured:
            refined_body = f"{body}\n\n[Refined with instruction: '{instruction}']"
            return GeneratedEmail(subject=subject, body=refined_body)

        prompt = textwrap.dedent(
            f"""
            You are a professional email writing assistant. Refine/rewrite the following email according to the user's instruction.
            
            ORIGINAL SUBJECT: {subject}
            ORIGINAL BODY:
            {body}
            
            INSTRUCTION: {instruction}
            TONE: {tone}
            LANGUAGE: {language}
            AUTHOR PROFILE:
            {profile_text}
            
            REQUIREMENTS:
            - Keep the tone {tone.lower()} and language {language} unless the instruction asks otherwise
            - Incorporate the author profile info naturally if required by the instruction
            - Modify both the subject and the body based on the instruction
            - The output should be a complete, ready-to-send email
            
            Return ONLY a JSON object with these exact keys:
            {{
                "subject": "Refined email subject line",
                "body": "Complete refined email body with proper formatting"
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
                ref_subject = data.get("subject") or subject
                ref_body = data.get("body") or body
            else:
                lines = [l.strip() for l in full_text.splitlines() if l.strip()]
                ref_subject = lines[0][:120] if lines else subject
                ref_body = "\n".join(lines[1:]) if len(lines) > 1 else full_text
            return GeneratedEmail(subject=ref_subject, body=ref_body.strip())
        except Exception:
            return GeneratedEmail(subject=subject, body=body)
