import time
import threading
import webview
from pathlib import Path
from typing import Dict, Any, List

from models.email_models import Provider, RecipientData, BulkEmailRequest, EmailRequest
from config.app_config import GEMINI_MODEL


class BulkMixin:
    # Native File Dialogs
    def select_attachments(self) -> List[Dict[str, Any]]:
        if not self.window:
            return []
        file_types = ("All files (*.*)",)
        files = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=file_types
        )
        if not files:
            return []
        
        result = []
        for f in files:
            path = Path(f)
            result.append({
                "name": path.name,
                "path": str(path),
                "size": path.stat().st_size
            })
        return result

    def select_csv_excel(self) -> Dict[str, Any]:
        if not self.window:
            return {"success": False, "error": "Window not initialized"}
        file_types = ("Data Files (*.csv;*.xlsx;*.xls)", "CSV Files (*.csv)", "Excel Files (*.xlsx;*.xls)")
        files = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=file_types
        )
        if not files or len(files) == 0:
            return {"success": False, "error": "No file selected"}
        
        file_path = files[0]
        try:
            path = Path(file_path)
            with open(file_path, "rb") as f:
                content = f.read()
            columns = self.file_parser.get_file_columns(content, path.name)
            return {
                "success": True,
                "filename": path.name,
                "path": str(path),
                "columns": columns
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Parsing
    def preview_bulk_data(
        self,
        file_path: str,
        name_column: str,
        email_column: str,
        description_column: str,
        custom_columns: Dict[str, str]
    ) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            with open(file_path, "rb") as f:
                content = f.read()
            preview, total = self.file_parser.preview_data(
                file_content=content,
                filename=path.name,
                name_column=name_column,
                email_column=email_column,
                description_column=description_column,
                custom_columns=custom_columns if custom_columns else None
            )
            return {"success": True, "preview": preview, "total": total}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def parse_bulk_data(
        self,
        file_path: str,
        name_column: str,
        email_column: str,
        description_column: str,
        custom_columns: Dict[str, str]
    ) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            with open(file_path, "rb") as f:
                content = f.read()
            recipients = self.file_parser.parse_file(
                file_content=content,
                filename=path.name,
                name_column=name_column,
                email_column=email_column,
                description_column=description_column,
                custom_columns=custom_columns if custom_columns else None
            )
            
            serialized = []
            for r in recipients:
                serialized.append({
                    "name": r.name,
                    "email": r.email,
                    "description": r.description,
                    "custom_fields": r.custom_fields or {}
                })
            
            valid_recipients, invalid_emails = self.file_parser.validate_email_addresses(recipients)
            
            return {
                "success": True,
                "recipients": serialized,
                "valid_count": len(valid_recipients),
                "invalid_emails": invalid_emails
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Previews & Workflow
    def generate_bulk_preview(
        self,
        provider: str,
        model_name: str,
        recipient: Dict[str, Any],
        bulk_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            use_ai = bulk_details.get("use_ai_generation", False)
            recipient_obj = RecipientData(
                name=recipient.get("name", ""),
                email=recipient.get("email", ""),
                description=recipient.get("description", ""),
                custom_fields=recipient.get("custom_fields", {})
            )
            
            if use_ai:
                ai_client = self._get_ai_client(provider, model_name)
                self.bulk_email_sender.ai_client = ai_client
                bulk_req = BulkEmailRequest(
                    provider=Provider.GMAIL,
                    sender_email="",
                    sender_password="",
                    subject="",
                    body_template="",
                    recipients=[recipient_obj],
                    use_ai_generation=True,
                    ai_purpose=bulk_details.get("ai_purpose", ""),
                    ai_tone=bulk_details.get("ai_tone", "Professional"),
                    ai_language=bulk_details.get("ai_language", "English"),
                    ai_length=bulk_details.get("ai_length", "Medium (3-4 paragraphs)"),
                    ai_additional_context=bulk_details.get("ai_additional_context", "")
                )
                
                profile = self.profile_store.load()
                sub, bdy = self.bulk_email_sender._generate_ai_email(bulk_req, recipient_obj, profile)
                return {"success": True, "subject": sub, "body": bdy, "method": "AI Generated"}
            else:
                subject_tpl = bulk_details.get("subject", "")
                body_tpl = bulk_details.get("body_template", "")
                sub = self.bulk_email_sender._personalize_email_body(subject_tpl, recipient_obj)
                bdy = self.bulk_email_sender._personalize_email_body(body_tpl, recipient_obj)
                return {"success": True, "subject": sub, "body": bdy, "method": "Template"}
        except Exception as e:
            try:
                recipient_obj = RecipientData(
                    name=recipient.get("name", ""),
                    email=recipient.get("email", ""),
                    description=recipient.get("description", ""),
                    custom_fields=recipient.get("custom_fields", {})
                )
                subject_tpl = bulk_details.get("subject", "")
                body_tpl = bulk_details.get("body_template", "")
                sub = self.bulk_email_sender._personalize_email_body(subject_tpl, recipient_obj)
                bdy = self.bulk_email_sender._personalize_email_body(body_tpl, recipient_obj)
                return {"success": True, "subject": sub, "body": bdy, "method": "Template (AI Failed)", "ai_error": str(e)}
            except Exception as e2:
                return {"success": False, "error": f"Failed preview: {str(e2)}"}

    # Direct Background Sends
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
            args=(smtp_details, bulk_details, recipients, delay_seconds, log_to_excel)
        )
        self.bulk_thread.daemon = True
        self.bulk_thread.start()
        return {"success": True}

    def cancel_bulk_sending(self) -> None:
        self.stop_bulk_sending = True

    def _run_direct_bulk_send(
        self,
        smtp_details: Dict[str, Any],
        bulk_details: Dict[str, Any],
        recipients: List[Dict[str, Any]],
        delay_seconds: float,
        log_to_excel: bool
    ) -> None:
        provider_str = smtp_details.get("provider", "Gmail").upper()
        sender_email = smtp_details.get("email", "")
        sender_password = smtp_details.get("password", "")
        provider = Provider.GMAIL if provider_str == "GMAIL" else Provider.OUTLOOK
        
        use_ai = bulk_details.get("use_ai_generation", False)
        ai_provider = bulk_details.get("ai_provider", "gemini")
        ai_model = bulk_details.get("ai_model", GEMINI_MODEL)
        
        ai_client = self._get_ai_client(ai_provider, ai_model) if use_ai else None
        self.bulk_email_sender.ai_client = ai_client
        profile = self.profile_store.load()
        
        total = len(recipients)
        success_count = 0
        failed_count = 0
        
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
            
            method = "Template"
            final_subject = ""
            final_body = ""
            if use_ai and ai_client:
                try:
                    bulk_req = BulkEmailRequest(
                        provider=provider,
                        sender_email=sender_email,
                        sender_password=sender_password,
                        subject="",
                        body_template="",
                        recipients=[recipient_obj],
                        use_ai_generation=True,
                        ai_purpose=bulk_details.get("ai_purpose", ""),
                        ai_tone=bulk_details.get("ai_tone", "Professional"),
                        ai_language=bulk_details.get("ai_language", "English"),
                        ai_length=bulk_details.get("ai_length", "Medium (3-4 paragraphs)"),
                        ai_additional_context=bulk_details.get("ai_additional_context", "")
                    )
                    sub, bdy = self.bulk_email_sender._generate_ai_email(bulk_req, recipient_obj, profile)
                    final_subject = sub
                    final_body = bdy
                    method = "AI"
                except Exception:
                    subject_tpl = bulk_details.get("subject", "")
                    body_tpl = bulk_details.get("body_template", "")
                    final_subject = self.bulk_email_sender._personalize_email_body(subject_tpl, recipient_obj)
                    final_body = self.bulk_email_sender._personalize_email_body(body_tpl, recipient_obj)
                    method = "Template (AI Failed)"
            else:
                subject_tpl = bulk_details.get("subject", "")
                body_tpl = bulk_details.get("body_template", "")
                final_subject = self.bulk_email_sender._personalize_email_body(subject_tpl, recipient_obj)
                final_body = self.bulk_email_sender._personalize_email_body(body_tpl, recipient_obj)
                method = "Template"

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
            
            status_str = "success" if success else "failed"
            self.history_store.append(
                provider=provider_str,
                sender=sender_email,
                recipient=recipient_obj.email,
                subject=final_subject,
                body=final_body,
                status=status_str,
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
                js_safe_name = recipient_obj.name.replace("'", "\\'")
                error_msg_js = error_msg.replace("'", "\\'").replace("\n", " ") if error_msg else ""
                self.window.evaluate_js(
                    f"updateBulkProgress({i + 1}, {total}, '{js_safe_name}', {'true' if success else 'false'}, '{method}', '{error_msg_js}')"
                )

            if delay_seconds > 0 and i < total - 1:
                time.sleep(delay_seconds)
                
        if self.window:
            self.window.evaluate_js(f"onBulkSendFinished({success_count}, {failed_count})")

    def parse_bulk_file(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            file_path = payload.get("path")
            if not file_path:
                return {"success": False, "error": "No file path provided"}
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            with open(path, "rb") as f:
                content = f.read()
            
            columns = self.file_parser.get_file_columns(content, path.name)
            
            import pandas as pd
            import io
            ext = path.suffix.lower()
            if ext == '.csv':
                df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(io.BytesIO(content))
            else:
                return {"success": False, "error": f"Unsupported file type: {ext}"}
            
            df = df.fillna("")
            rows = df.to_dict(orient="records")
            
            return {
                "success": True,
                "rows": rows,
                "columns": columns
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def preview_bulk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rows = payload.get("rows", [])
            purpose = payload.get("purpose", "")
            subject_tpl = payload.get("subject", "")
            
            previews = []
            for r in rows[:5]:
                name = r.get("Name") or r.get("name") or r.get("recipient_name") or ""
                email = r.get("Email") or r.get("email") or r.get("recipient_email") or ""
                desc = r.get("Description") or r.get("description") or r.get("purpose") or ""
                
                subject = subject_tpl
                for k, v in r.items():
                    subject = subject.replace(f"{{{{{k}}}}}", str(v))
                
                previews.append({
                    "Name": name,
                    "Email": email,
                    "Subject": subject,
                    "Description": desc
                })
            return {"success": True, "previews": previews}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_bulk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rows = payload.get("rows", [])
            purpose = payload.get("purpose", "")
            provider = payload.get("ai_provider", "gemini")
            model_name = payload.get("model", "")
            subject_tpl = payload.get("subject", "")

            if not model_name:
                settings = self.settings_store.load()
                provider = settings.get("ai_provider", "gemini")
                model_name = settings.get(f"{provider}_model", GEMINI_MODEL)

            ai_client = self._get_ai_client(provider, model_name)
            profile = self.profile_store.load()
            
            emails = []
            for r in rows:
                name = r.get("Name") or r.get("name") or r.get("recipient_name") or "Recipient"
                email = r.get("Email") or r.get("email") or r.get("recipient_email") or ""
                desc = r.get("Description") or r.get("description") or r.get("purpose") or ""
                
                # Build personalized prompt context
                personalized_context = f"Recipient: {name} ({email})\nDescription: {desc}\n"
                for k, v in r.items():
                    if k.lower() not in ["name", "email", "description"]:
                        personalized_context += f"- {k}: {v}\n"
                
                try:
                    res = ai_client.generate_email(
                        purpose=purpose,
                        recipient_name=name,
                        tone="Professional",
                        language="Turkish",
                        additional_context=personalized_context,
                        profile=profile,
                        email_length="Medium (3-4 paragraphs)"
                    )
                    subject = res.subject
                    body = res.body
                except Exception as e:
                    # Fallback to template personalization
                    subject = subject_tpl
                    body = f"Merhaba {name},\n\nŞirketiniz {desc} ile ilgili..."
                    for k, v in r.items():
                        subject = subject.replace(f"{{{{{k}}}}}", str(v))
                        body = body.replace(f"{{{{{k}}}}}", str(v))
                
                emails.append({
                    "to": email,
                    "subject": subject,
                    "body": body,
                    "recipient_name": name
                })
                
            return {"success": True, "emails": emails}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_bulk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            emails = payload.get("emails", [])
            smtp_provider = payload.get("smtp_provider", "Gmail")
            smtp_email = payload.get("smtp_email", "")
            smtp_password = payload.get("smtp_password", "")
            delay_seconds = float(payload.get("delay_seconds", 2.0))
            log_id = payload.get("log_id", "bulk")

            def js_log(msg: str):
                try:
                    safe = msg.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
                    if hasattr(self, 'window') and self.window:
                        self.window.evaluate_js(f"appendSmtpLog('{log_id}', '{safe}')")
                except Exception:
                    pass

            sent = 0
            total = len(emails)
            js_log(f"[BULK] Starting: {total} emails via {smtp_provider}")
            for i, email_data in enumerate(emails):
                recipient = email_data.get("to")
                subject = email_data.get("subject")
                body = email_data.get("body")
                js_log(f"[{i+1}/{total}] → {recipient}")
                
                # Send single email
                res = self.send_single_email(
                    provider=smtp_provider,
                    sender_email=smtp_email,
                    sender_password=smtp_password,
                    recipient_email=recipient,
                    subject=subject,
                    body=body,
                    attachment_paths=[],
                    log_to_excel=True,
                    log_cb=None  # already using bulk log
                )
                if res.get("success"):
                    sent += 1
                    js_log(f"  ✔ Sent to {recipient}")
                else:
                    js_log(f"  ✘ Failed: {res.get('error', '')[:80]}")
                
                if delay_seconds > 0 and i < total - 1:
                    time.sleep(delay_seconds)
            
            js_log(f"[BULK] Done: {sent}/{total} sent successfully")
            return {
                "success": True,
                "sent": sent,
                "total": total
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

