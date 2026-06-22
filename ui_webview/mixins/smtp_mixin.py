import traceback
import webview
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from models.email_models import EmailRequest, Provider, Attachment


class SmtpMixin:
    """SMTP send, test, and file-picker methods."""

    def send_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            smtp_provider    = payload.get("smtp_provider", "Gmail")
            smtp_email       = payload.get("smtp_email", "")
            smtp_password    = payload.get("smtp_password", "")
            to_email         = payload.get("to_email", "")
            subject          = payload.get("subject", "")
            body             = payload.get("body", "")
            attachment_paths = payload.get("attachments", [])
            log_id           = payload.get("log_id", "single")

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

            if log_cb:
                log_cb(f"[SMTP] Building email payload (attachments: {len(attachments)})…")

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

            if log_cb:
                log_cb(f"[SMTP] Authenticating as {sender_email}…")
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

    def pick_files(self, payload: Dict[str, Any] = None) -> List[str]:
        if not self.window:
            return []
        payload       = payload or {}
        multiple      = payload.get("multiple", False)
        file_types    = payload.get("file_types", ["All files (*.*)"])
        formatted     = []
        for ft in file_types:
            if ft.startswith('.'):
                ext = ft[1:].upper()
                formatted.append(f"{ext} Files (*{ft})")
            else:
                formatted.append(ft)
        if not formatted:
            formatted = ["All files (*.*)"]
        files = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=multiple,
            file_types=tuple(formatted)
        )
        return list(files) if files else []

    def test_smtp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            provider = payload.get("smtp_provider", "Gmail").lower()
            email    = payload.get("smtp_email", "")
            password = payload.get("smtp_password", "")
            if not email or not password:
                return {"success": False, "error": "Email and password are required"}

            import ssl, smtplib
            context = ssl.create_default_context()

            if provider == "outlook":
                host, port = "smtp-mail.outlook.com", 587
                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(email, password)
            else:  # Gmail / default
                host, port = "smtp.gmail.com", 587
                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(email, password)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"{e.__class__.__name__}: {e}"}
