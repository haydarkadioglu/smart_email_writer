import os
import json
import time
import datetime
import traceback
import webview
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

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

    def analyze_email_tone(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Use the active AI provider to analyse tone of an email draft."""
        try:
            provider = payload.get("ai_provider", "gemini")
            model_name = payload.get("model", "")
            body = payload.get("body", "")
            if not body.strip():
                return {"success": False, "error": "Email body is empty."}

            prompt = (
                "Analyze the tone of this email and return ONLY valid JSON (no markdown, no explanation) "
                "with these exact keys: formality (0-100), friendliness (0-100), urgency (0-100), "
                "clarity (0-100), advice (a short 1-sentence tip to improve the email).\n\nEmail:\n" + body
            )

            ai_client = self._get_ai_client(provider, model_name)
            # Use a direct text completion call
            raw = ai_client._call_raw(prompt)
            # Strip markdown code fences if any
            raw = raw.strip().strip("```json").strip("```").strip()
            data = json.loads(raw)
            self._log_usage(provider, model_name, prompt + body, raw)
            return {"success": True, "data": data}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"AI returned non-JSON response: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _log_usage(self, provider: str, model: str, prompt_text: str, response_text: str):
        """Estimate token usage and append to config/usage_logs.json."""
        try:
            tokens_in  = max(1, len(prompt_text) // 4)
            tokens_out = max(1, len(response_text) // 4)
            # Approximate cost per 1K tokens in USD (rough estimates)
            cost_map = {
                "gemini":     (0.0000375, 0.00015),
                "groq":       (0.00005,   0.0001),
                "openai":     (0.005,     0.015),
                "claude":     (0.003,     0.015),
                "deepseek":   (0.00014,   0.00028),
                "openrouter": (0.001,     0.002),
            }
            in_rate, out_rate = cost_map.get(provider.lower(), (0.001, 0.002))
            cost_usd = (tokens_in / 1000) * in_rate + (tokens_out / 1000) * out_rate

            log_path = Path("config") / "usage_logs.json"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                logs = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
            except Exception:
                logs = []
            logs.append({
                "ts":         datetime.datetime.now().isoformat(timespec="seconds"),
                "provider":   provider,
                "model":      model,
                "tokens_in":  tokens_in,
                "tokens_out": tokens_out,
                "cost_usd":   round(cost_usd, 6),
            })
            log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass  # Never crash the main flow for logging

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
            self._log_usage(provider, model_name, purpose, res.body)
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
            self._log_usage(provider, model_name, instruction + body, res.body)
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
            log_id = payload.get("log_id", "single")

            def js_log(msg: str):
                try:
                    safe = msg.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
                    if hasattr(self, 'window') and self.window:
                        self.window.evaluate_js(f"appendSmtpLog('{log_id}', '{safe}')")
                except Exception:
                    pass

            js_log(f"[SMTP] Connecting to {smtp_provider}…")
            result = self.send_single_email(
                provider=smtp_provider,
                sender_email=smtp_email,
                sender_password=smtp_password,
                recipient_email=to_email,
                subject=subject,
                body=body,
                attachment_paths=attachment_paths,
                log_to_excel=True,
                log_cb=js_log
            )
            if result.get("success"):
                js_log(f"[SMTP] ✔ Message delivered to {to_email}")
            else:
                js_log(f"[SMTP] ✘ Failed: {result.get('error', '')}")
            return result
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
        log_to_excel: bool,
        log_cb: Optional[Callable[[str], None]] = None
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

            if log_cb: log_cb(f"[SMTP] Building email payload (attachments: {len(attachments)})…")

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

            if log_cb: log_cb(f"[SMTP] Authenticating as {sender_email}…")
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
