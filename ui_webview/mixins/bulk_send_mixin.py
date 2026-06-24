import time
import threading
from typing import Dict, Any, List

from models.email_models import RecipientData, BulkEmailRequest, EmailRequest, Provider
from config.app_config import GEMINI_MODEL


class BulkSendMixin:
    """Background bulk sending and per-email sending logic."""

    # ── Thread control ─────────────────────────────────────────────────────

    def start_direct_bulk_send(
        self,
        smtp_details: Dict[str, Any],
        bulk_details: Dict[str, Any],
        recipients: List[Dict[str, Any]],
        delay_seconds: float,
        log_to_excel: bool
    ) -> Dict[str, Any]:
        if self.bulk_thread and self.bulk_thread.is_alive():
            return {"success": False, "error": "A bulk sending task is already running"}

        self.stop_bulk_sending = False
        self.bulk_thread = threading.Thread(
            target=self._run_direct_bulk_send,
            args=(smtp_details, bulk_details, recipients, delay_seconds, log_to_excel),
            daemon=True
        )
        self.bulk_thread.start()
        return {"success": True}

    def cancel_bulk_sending(self) -> None:
        self.stop_bulk_sending = True

    # ── Main loop ──────────────────────────────────────────────────────────

    def _run_direct_bulk_send(
        self,
        smtp_details: Dict[str, Any],
        bulk_details: Dict[str, Any],
        recipients: List[Dict[str, Any]],
        delay_seconds: float,
        log_to_excel: bool
    ) -> None:
        provider_str    = smtp_details.get("provider", "Gmail").upper()
        sender_email    = smtp_details.get("email", "")
        sender_password = smtp_details.get("password", "")
        provider        = Provider.GMAIL if provider_str == "GMAIL" else Provider.OUTLOOK

        use_ai     = bulk_details.get("use_ai_generation", False)
        ai_provider = bulk_details.get("ai_provider", "gemini")
        ai_model   = bulk_details.get("ai_model", GEMINI_MODEL)

        profile  = self.profile_store.load()
        total    = len(recipients)
        success_count = failed_count = 0

        for i, r in enumerate(recipients):
            if self.stop_bulk_sending:
                if self.window:
                    self.window.evaluate_js("onBulkSendCancelled()")
                return

            recipient_obj = RecipientData(
                name=r.get("name", ""),
                email=r.get("email", ""),
                description=r.get("description", ""),
                custom_fields=r.get("custom_fields", {})
            )

            final_subject, final_body, method = self._prepare_email_content(
                use_ai, ai_provider, ai_model, bulk_details, recipient_obj, provider,
                sender_email, sender_password, profile
            )

            request = EmailRequest(
                provider=provider,
                sender_email=sender_email,
                sender_password=sender_password,
                recipient_email=recipient_obj.email,
                subject=final_subject,
                body=final_body,
                attachments=None
            )
            success, error_msg = self.email_sender.send(request)

            self.history_store.append(
                provider=provider_str,
                sender=sender_email,
                recipient=recipient_obj.email,
                subject=final_subject,
                body=final_body,
                status="success" if success else "failed",
                error_message=error_msg
            )

            if success:
                success_count += 1
                if log_to_excel:
                    try:
                        self.excel_logger.append(
                            sender_email=sender_email,
                            recipient_email=recipient_obj.email,
                            subject=final_subject,
                            body=final_body,
                            provider=provider_str
                        )
                    except Exception:
                        pass
            else:
                failed_count += 1

            if self.window:
                js_name = recipient_obj.name.replace("'", "\\'")
                js_err  = (error_msg or "").replace("'", "\\'").replace("\n", " ")
                self.window.evaluate_js(
                    f"updateBulkProgress({i+1},{total},'{js_name}',{'true' if success else 'false'},'{method}','{js_err}')"
                )

            if delay_seconds > 0 and i < total - 1:
                time.sleep(delay_seconds)

        if self.window:
            self.window.evaluate_js(f"onBulkSendFinished({success_count},{failed_count})")

    def _prepare_email_content(
        self, use_ai, ai_provider, ai_model, bulk_details, recipient_obj,
        provider, sender_email, sender_password, profile
    ):
        if use_ai:
            try:
                def do_prep(client, p, m):
                    self.bulk_email_sender.ai_client = client
                    bulk_req = BulkEmailRequest(
                        provider=provider,
                        sender_email=sender_email,
                        sender_password=sender_password,
                        subject="", body_template="",
                        recipients=[recipient_obj],
                        use_ai_generation=True,
                        ai_purpose=bulk_details.get("ai_purpose", ""),
                        ai_tone=bulk_details.get("ai_tone", "Professional"),
                        ai_language=bulk_details.get("ai_language", "English"),
                        ai_length=bulk_details.get("ai_length", "Medium (3-4 paragraphs)"),
                        ai_additional_context=bulk_details.get("ai_additional_context", "")
                    )
                    return self.bulk_email_sender._generate_ai_email(bulk_req, recipient_obj, profile)
                
                sub, bdy = self._execute_with_fallback(ai_provider, ai_model, do_prep)
                return sub, bdy, "AI"
            except Exception:
                pass  # Fall through to template
        subject_tpl = bulk_details.get("subject", "")
        body_tpl    = bulk_details.get("body_template", "")
        sub = self.bulk_email_sender._personalize_email_body(subject_tpl, recipient_obj)
        bdy = self.bulk_email_sender._personalize_email_body(body_tpl, recipient_obj)
        method = "Template (AI Failed)" if use_ai else "Template"
        return sub, bdy, method

    # ── Per-email SMTP send (used by new bulk flow) ────────────────────────

    def send_bulk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            emails         = payload.get("emails", [])
            smtp_provider  = payload.get("smtp_provider", "Gmail")
            smtp_email     = payload.get("smtp_email", "")
            smtp_password  = payload.get("smtp_password", "")
            delay_seconds  = float(payload.get("delay_seconds", 2.0))
            log_id         = payload.get("log_id", "bulk")

            def js_log(msg: str):
                try:
                    safe = msg.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
                    if hasattr(self, "window") and self.window:
                        self.window.evaluate_js(f"appendSmtpLog('{log_id}', '{safe}')")
                except Exception:
                    pass

            sent  = 0
            total = len(emails)
            js_log(f"[BULK] Starting: {total} emails via {smtp_provider}")
            for i, email_data in enumerate(emails):
                recipient = email_data.get("to")
                subject   = email_data.get("subject")
                body      = email_data.get("body")
                js_log(f"[{i+1}/{total}] → {recipient}")
                res = self.send_single_email(
                    provider=smtp_provider,
                    sender_email=smtp_email,
                    sender_password=smtp_password,
                    recipient_email=recipient,
                    subject=subject,
                    body=body,
                    attachment_paths=[],
                    log_to_excel=True,
                    log_cb=None
                )
                if res.get("success"):
                    sent += 1
                    js_log(f"  ✔ Sent to {recipient}")
                else:
                    js_log(f"  ✘ Failed: {res.get('error', '')[:80]}")
                if delay_seconds > 0 and i < total - 1:
                    time.sleep(delay_seconds)
            js_log(f"[BULK] Done: {sent}/{total} sent successfully")
            return {"success": True, "sent": sent, "total": total}
        except Exception as e:
            return {"success": False, "error": str(e)}
