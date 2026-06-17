import os
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional

from models.email_models import EmailRequest, Provider, Attachment
from clients.gemini_client import GeminiClient
from clients.groq_client import GroqClient
from clients.openai_client import OpenAIClient
from clients.claude_client import ClaudeClient
from clients.deepseek_client import DeepSeekClient
from clients.openrouter_client import OpenRouterClient


class EmailMixin:

    def _get_ai_client(self, provider: str, model_name: str):
        """Return the appropriate AI client for the given provider string."""
        p = provider.lower()
        key = lambda env: os.getenv(env, "")

        if p == "groq":
            return GroqClient(api_key=key("GROQ_API_KEY"), model_name=model_name)
        elif p == "openai":
            return OpenAIClient(api_key=key("OPENAI_API_KEY"), model_name=model_name)
        elif p == "claude":
            return ClaudeClient(api_key=key("CLAUDE_API_KEY"), model_name=model_name)
        elif p == "deepseek":
            return DeepSeekClient(api_key=key("DEEPSEEK_API_KEY"), model_name=model_name)
        elif p == "openrouter":
            return OpenRouterClient(api_key=key("OPENROUTER_API_KEY"), model_name=model_name)
        else:  # default: gemini
            return GeminiClient(api_key=key("GEMINI_API_KEY"), model_name=model_name)

    def analyze_email(self, subject: str, body: str, language: str = "English") -> Dict[str, Any]:
        try:
            return self.spam_analyzer.analyze(subject, body, language)
        except Exception as e:
            return {"error": str(e)}

    def generate_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            provider = payload.get("ai_provider", "gemini")
            model_name = payload.get("model", "")
            purpose = payload.get("purpose", "")
            recipient_name = payload.get("receiver", "")
            company = payload.get("company", "")
            tone = payload.get("tone", "Professional")
            language = payload.get("language", "Turkish")
            additional_context = payload.get("additional_context", "")
            email_length = payload.get("email_length", "Medium (3-4 paragraphs)")

            # Incorporate company into additional_context if provided
            if company:
                additional_context = f"Company: {company}\n{additional_context}"

            ai_client = self._get_ai_client(provider, model_name)
            profile = self.profile_store.load()
            res = ai_client.generate_email(
                purpose=purpose,
                recipient_name=recipient_name,
                tone=tone,
                language=language,
                additional_context=additional_context,
                profile=profile,
                email_length=email_length
            )
            return {"success": True, "subject": res.subject, "email": res.body}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def refine_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            provider = payload.get("ai_provider", "gemini")
            model_name = payload.get("model", "")
            body = payload.get("current_email", "")
            instruction = payload.get("instruction", "")
            tone = payload.get("tone", "Professional")
            language = payload.get("language", "Turkish")

            ai_client = self._get_ai_client(provider, model_name)
            profile = self.profile_store.load()
            res = ai_client.refine_email(
                subject="",
                body=body,
                instruction=instruction,
                tone=tone,
                language=language,
                profile=profile
            )
            return {"success": True, "subject": res.subject, "email": res.body}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            smtp_provider = payload.get("smtp_provider", "Gmail")
            smtp_email = payload.get("smtp_email", "")
            smtp_password = payload.get("smtp_password", "")
            to_email = payload.get("to_email", "")
            subject = payload.get("subject", "")
            body = payload.get("body", "")
            attachment_paths = payload.get("attachments", [])

            return self.send_single_email(
                provider=smtp_provider,
                sender_email=smtp_email,
                sender_password=smtp_password,
                recipient_email=to_email,
                subject=subject,
                body=body,
                attachment_paths=attachment_paths,
                log_to_excel=True
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    def pick_files(self, payload: Dict[str, Any] = None) -> List[str]:
        if not self.window:
            return []
        payload = payload or {}
        multiple = payload.get("multiple", False)
        file_types = payload.get("file_types", ["All files (*.*)"])
        
        formatted_types = []
        for ft in file_types:
            if ft.startswith('.'):
                ext = ft[1:].upper()
                formatted_types.append(f"{ext} Files (*{ft})")
            else:
                formatted_types.append(ft)
        
        if not formatted_types:
            formatted_types = ["All files (*.*)"]
            
        files = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=multiple,
            file_types=tuple(formatted_types)
        )
        return list(files) if files else []

    def test_smtp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            provider = payload.get("smtp_provider", "Gmail").lower()
            email = payload.get("smtp_email", "")
            password = payload.get("smtp_password", "")
            if not email or not password:
                return {"success": False, "error": "Email and password are required"}

            import ssl
            import smtplib
            context = ssl.create_default_context()
            
            if provider == "outlook":
                host, port = "smtp-mail.outlook.com", 587
                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(email, password)
            else: # Gmail / default
                host, port = "smtp.gmail.com", 587
                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(email, password)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"{e.__class__.__name__}: {e}"}

    def send_single_email(
        self,
        provider: str,
        sender_email: str,
        sender_password: str,
        recipient_email: str,
        subject: str,
        body: str,
        attachment_paths: List[str],
        log_to_excel: bool
    ) -> Dict[str, Any]:
        try:
            attachments = []
            for path_str in attachment_paths:
                path = Path(path_str)
                if path.exists():
                    with open(path, "rb") as f:
                        content = f.read()
                    attachments.append(Attachment(
                        filename=path.name,
                        content=content,
                        mime_type="application/octet-stream"
                    ))

            enum_provider = Provider.GMAIL if provider.lower() == "gmail" else Provider.OUTLOOK
            request = EmailRequest(
                provider=enum_provider,
                sender_email=sender_email,
                sender_password=sender_password,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                attachments=attachments if attachments else None
            )

            success, error_msg = self.email_sender.send(request)

            status_str = "success" if success else "failed"
            self.history_store.append(
                provider=provider.upper(),
                sender=sender_email,
                recipient=recipient_email,
                subject=subject,
                body=body,
                status=status_str,
                error_message=error_msg
            )

            if success:
                if log_to_excel:
                    try:
                        self.excel_logger.append(
                            sender_email=sender_email,
                            recipient_email=recipient_email,
                            subject=subject,
                            body=body,
                            provider=provider.upper()
                        )
                    except Exception as le:
                        print(f"Failed to log to Excel: {le}")
                return {"success": True}
            else:
                return {"success": False, "error": error_msg}
        except Exception as e:
            return {"success": False, "error": f"{e.__class__.__name__}: {e}\n{traceback.format_exc()}"}
