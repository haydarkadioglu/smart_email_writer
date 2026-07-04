"""
Base class for OpenAI-compatible chat completion providers.
Used by: OpenAI, Claude (via openai-compat), DeepSeek, OpenRouter.
All three expose the same `/v1/chat/completions` endpoint format.
"""
import json
import textwrap
from typing import Optional, Dict, Any

from models.email_models import GeneratedEmail


def _build_profile_text(profile: Optional[Dict[str, Any]]) -> str:
    if not profile:
        return ""
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
    extras = []
    for k, v in profile.items():
        if v:
            label = friendly_names.get(k, k.replace("_", " ").title())
            extras.append(f"{label}: {v}")
    return "\n".join(extras)


def _parse_json_response(text: str, fallback_subject: str, fallback_body: str):
    """Try to extract {subject, body} JSON from a model response."""
    import re
    # strip markdown fences
    text = re.sub(r"```(?:json)?", "", text).strip()
    # find first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data.get("subject") or fallback_subject, (data.get("body") or fallback_body).strip()
        except Exception:
            pass
    # heuristic fallback
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    subject = lines[0][:120] if lines else fallback_subject
    body = "\n".join(lines[1:]) if len(lines) > 1 else text
    return subject, body.strip()


class OpenAICompatClient:
    """
    Generic wrapper for any OpenAI-compatible /v1/chat/completions provider.
    Subclasses set `base_url`, `provider_name`, and `default_model`.
    """
    base_url: str = "https://api.openai.com/v1"
    provider_name: str = "OpenAI"
    default_model: str = "gpt-4o-mini"

    def __init__(self, api_key: str = "", model_name: str = "") -> None:
        self.api_key   = api_key
        self.model_name = model_name or self.default_model
        self._client   = None
        self._configured = False
        self._init_error: Optional[Exception] = None

        try:
            from openai import OpenAI          # type: ignore
            if not api_key:
                raise ValueError(
                    f"{self.provider_name} API key missing. "
                    f"Add it to your .env file and restart."
                )
            self._client = OpenAI(api_key=api_key, base_url=self.base_url)
            self._configured = True
        except ImportError:
            self._init_error = ImportError(
                "openai package not installed. Run: pip install openai"
            )
        except Exception as e:
            self._init_error = e

    # ── internal ──────────────────────────────────────────────────────────
    def _call_raw(self, prompt: str) -> str:
        """Send a raw user-only prompt and return the model response as a string."""
        if not self._configured:
            raise RuntimeError(str(self._init_error))
        resp = self._client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return resp.choices[0].message.content if resp and resp.choices else ""

    def _call_raw_stream(self, prompt: str, chunk_cb=None) -> str:
        """Stream a raw prompt; calls chunk_cb(text) for each delta. Returns full text."""
        if not self._configured:
            raise RuntimeError(str(self._init_error))
        full_text = ""
        with self._client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            stream=True,
        ) as stream:
            for chunk in stream:
                delta = chunk.choices[0].delta.content or "" if chunk.choices else ""
                full_text += delta
                if delta and chunk_cb:
                    chunk_cb(delta)
        return full_text

    def _chat(self, system: str, user: str) -> str:
        if not self._configured:
            raise RuntimeError(str(self._init_error))
        resp = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.7,
        )
        return resp.choices[0].message.content if resp and resp.choices else ""

    # ── Public API (same interface as GeminiClient / GroqClient) ──────────
    def generate_email(
        self,
        purpose: str,
        recipient_name: str,
        tone: str = "Professional",
        language: str = "English",
        additional_context: str = "",
        profile: Optional[Dict[str, Any]] = None,
        email_length: str = "Medium (3-4 paragraphs)",
    ) -> GeneratedEmail:
        profile_text = _build_profile_text(profile)

        system_prompt = textwrap.dedent(f"""
            You are a professional email writing assistant.
            Write a complete, {tone.lower()} email in {language}.
            Email length rules (STRICT):
            - "Very Short (1 paragraph)": Use EXACTLY this structure, each part on its OWN line separated by a blank line:
                Greeting (e.g. Dear [Name],)
                [blank line]
                ONE paragraph of 2-3 sentences max.
                [blank line]
                Closing (e.g. Best regards,) + sender name.
                NEVER merge the greeting, body and closing into one continuous block.
            - "Short (1-2 paragraphs)": greeting + 1-2 short paragraphs + closing on separate lines.
            - "Medium (3-4 paragraphs)": standard structured email.
            - "Long (5+ paragraphs)": detailed email.
            Current requested length: {email_length}.

            CRITICAL RULES:
            0. PURPOSE IS #1: The email must be laser-focused on the user's stated purpose. Do NOT drift, add unrelated content, or change the intent. Everything else (profile, context) is secondary personalization only.
            1. ATTACHMENTS: Only reference files that are explicitly mentioned as attached in the prompt/context. If only a CV/resume is attached, do NOT write "including my CV and academic certificates / references / transcripts / cover letter". ONLY mention the CV. Never assume or hallucinate attachments that were not uploaded by the user.
            2. LINKS/WEBSITES: If the author's profile contains a Website, GitHub, or LinkedIn, and the email is an application, cover letter, or introductory email, you MUST naturally include these links in the body (e.g., "My portfolio is available at [Website]" or "You can find my projects at [GitHub]"). Do not omit them.

            Return ONLY a JSON object with keys "subject" and "body".
        """).strip()

        user_prompt = textwrap.dedent(f"""
            *** PRIMARY GOAL — stay laser-focused on this, do NOT deviate ***
            PURPOSE: {purpose}
            *** End of primary goal ***

            RECIPIENT: {recipient_name}
            ADDITIONAL CONTEXT (for personalization only, do not override the purpose above): {additional_context}
            AUTHOR PROFILE:
            {profile_text}
        """).strip()

        try:
            text = self._chat(system_prompt, user_prompt)
            subject, body = _parse_json_response(
                text, f"Regarding: {purpose}", text
            )
            return GeneratedEmail(subject=subject, body=body)
        except Exception as e:
            raise RuntimeError(f"{self.provider_name} generation failed: {e}")

    def refine_email(
        self,
        subject: str,
        body: str,
        instruction: str,
        tone: str = "Professional",
        language: str = "English",
        profile: Optional[Dict[str, Any]] = None,
    ) -> GeneratedEmail:
        if not instruction:
            return GeneratedEmail(subject=subject, body=body)

        profile_text = _build_profile_text(profile)

        system_prompt = textwrap.dedent(f"""
            You are a professional email writing assistant.
            Refine the email based on the instruction.
            Keep tone {tone.lower()} and language {language} unless instructed otherwise.
            Return ONLY a JSON object with keys "subject" and "body".
        """).strip()

        user_prompt = textwrap.dedent(f"""
            ORIGINAL SUBJECT: {subject}
            ORIGINAL BODY:
            {body}

            INSTRUCTION: {instruction}
            AUTHOR PROFILE:
            {profile_text}
        """).strip()

        try:
            text = self._chat(system_prompt, user_prompt)
            ref_subject, ref_body = _parse_json_response(text, subject, body)
            return GeneratedEmail(subject=ref_subject, body=ref_body)
        except Exception as e:
            raise RuntimeError(f"{self.provider_name} refinement failed: {e}")
