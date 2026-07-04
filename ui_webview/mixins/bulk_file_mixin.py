import webview
import pandas as pd
import io
from pathlib import Path
from typing import Dict, Any, List

from models.email_models import RecipientData, BulkEmailRequest, Provider
from config.app_config import GEMINI_MODEL


class BulkFileMixin:
    """File selection, parsing, preview and email generation for bulk emails."""

    # ── Native file dialogs ────────────────────────────────────────────────

    def select_attachments(self) -> List[Dict[str, Any]]:
        if not self.window:
            return []
        files = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=("All files (*.*)",)
        )
        if not files:
            return []
        result = []
        for f in files:
            path = Path(f)
            result.append({"name": path.name, "path": str(path), "size": path.stat().st_size})
        return result

    def select_csv_excel(self) -> Dict[str, Any]:
        if not self.window:
            return {"success": False, "error": "Window not initialized"}
        file_types = (
            "Data Files (*.csv;*.xlsx;*.xls)",
            "CSV Files (*.csv)",
            "Excel Files (*.xlsx;*.xls)",
        )
        files = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=file_types
        )
        if not files:
            return {"success": False, "error": "No file selected"}
        file_path = files[0]
        try:
            path = Path(file_path)
            with open(file_path, "rb") as f:
                content = f.read()
            columns = self.file_parser.get_file_columns(content, path.name)
            return {"success": True, "filename": path.name, "path": str(path), "columns": columns}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Parsing ────────────────────────────────────────────────────────────

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
            ext = path.suffix.lower()
            if ext == ".csv":
                df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
            elif ext in [".xlsx", ".xls"]:
                df = pd.read_excel(io.BytesIO(content))
            else:
                return {"success": False, "error": f"Unsupported file type: {ext}"}

            df = df.fillna("")
            rows = df.to_dict(orient="records")
            return {"success": True, "rows": rows, "columns": columns}
        except Exception as e:
            return {"success": False, "error": str(e)}

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
            serialized = [
                {"name": r.name, "email": r.email, "description": r.description, "custom_fields": r.custom_fields or {}}
                for r in recipients
            ]
            valid_recipients, invalid_emails = self.file_parser.validate_email_addresses(recipients)
            return {
                "success": True,
                "recipients": serialized,
                "valid_count": len(valid_recipients),
                "invalid_emails": invalid_emails,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Preview & generate ─────────────────────────────────────────────────

    def preview_bulk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rows        = payload.get("rows", [])
            subject_tpl = payload.get("subject", "")
            previews = []
            for r in rows[:5]:
                name  = r.get("Name") or r.get("name") or r.get("recipient_name") or ""
                email = r.get("Email") or r.get("email") or r.get("recipient_email") or ""
                desc  = r.get("Description") or r.get("description") or r.get("purpose") or ""
                subject = subject_tpl
                for k, v in r.items():
                    subject = subject.replace(f"{{{{{k}}}}}", str(v))
                previews.append({"Name": name, "Email": email, "Subject": subject, "Description": desc})
            return {"success": True, "previews": previews}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_bulk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rows        = payload.get("rows", [])
            purpose     = payload.get("purpose", "")
            provider    = payload.get("ai_provider", "gemini")
            model_name  = payload.get("model", "")
            subject_tpl = payload.get("subject", "")

            if not model_name:
                settings   = self.settings_store.load()
                provider   = settings.get("ai_provider", "gemini")
                model_name = settings.get(f"{provider}_model", GEMINI_MODEL)

            profile = self.profile_store.load()
            total   = len(rows)
            emails  = []

            for i, r in enumerate(rows):
                # Capture values in local scope to avoid closure-in-loop bug
                _name    = (r.get("Name") or r.get("name") or r.get("recipient_name") or "Recipient").strip()
                _email   = (r.get("Email") or r.get("email") or r.get("recipient_email") or "").strip()
                _desc    = (r.get("Description") or r.get("description") or r.get("purpose") or "").strip()
                _company = (r.get("Company") or r.get("company") or "").strip()

                # Report progress to UI
                if hasattr(self, "window") and self.window:
                    safe_name = _name.replace("'", "\\'")
                    self.window.evaluate_js(
                        f"updateBulkProgress({i}, {total}, '{safe_name}', true, 'AI', '')"
                    )

                personalized_context = f"Recipient: {_name}\nEmail: {_email}\n"
                if _company:
                    personalized_context += f"Company: {_company}\n"
                if _desc:
                    personalized_context += f"Context: {_desc}\n"
                for k, v in r.items():
                    if k.lower() not in ["name", "email", "description", "company",
                                         "Name", "Email", "Company", "Description"]:
                        personalized_context += f"- {k}: {v}\n"

                try:
                    # Capture loop variables in a default-arg closure to avoid late binding
                    def do_generate(client, p, m,
                                    _n=_name, _pur=purpose, _ctx=personalized_context, _pr=profile):
                        return client.generate_email(
                            purpose=_pur,
                            recipient_name=_n,
                            tone="Professional",
                            language="Turkish",
                            additional_context=_ctx,
                            profile=_pr,
                            email_length="Medium (3-4 paragraphs)"
                        )
                    res     = self._execute_with_fallback(provider, model_name, do_generate)
                    subject = res.subject
                    body    = res.body
                except Exception as gen_err:
                    # Fallback to simple template
                    subject = subject_tpl or f"Merhaba {_name}"
                    body    = f"Merhaba {_name},\n\n{purpose}\n\nSaygılarımla"
                    for k, v in r.items():
                        subject = str(subject).replace(f"{{{{{k}}}}}", str(v))
                        body    = str(body).replace(f"{{{{{k}}}}}", str(v))

                emails.append({"to": _email, "subject": subject, "body": body, "recipient_name": _name})

            # Final progress update
            if hasattr(self, "window") and self.window:
                self.window.evaluate_js(
                    f"updateBulkProgress({total}, {total}, 'Done', true, 'AI', '')"
                )

            return {"success": True, "emails": emails}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_bulk_preview(
        self,
        provider: str,
        model_name: str,
        recipient: Dict[str, Any],
        bulk_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            use_ai       = bulk_details.get("use_ai_generation", False)
            recipient_obj = RecipientData(
                name=recipient.get("name", ""),
                email=recipient.get("email", ""),
                description=recipient.get("description", ""),
                custom_fields=recipient.get("custom_fields", {})
            )
            if use_ai:
                def do_generate_preview(client, p, m):
                    self.bulk_email_sender.ai_client = client
                    bulk_req = BulkEmailRequest(
                        provider=Provider.GMAIL,
                        sender_email="", sender_password="",
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

                profile = self.profile_store.load()
                sub, bdy = self._execute_with_fallback(provider, model_name, do_generate_preview)
                return {"success": True, "subject": sub, "body": bdy, "method": "AI Generated"}
            else:
                subject_tpl = bulk_details.get("subject", "")
                body_tpl    = bulk_details.get("body_template", "")
                sub = self.bulk_email_sender._personalize_email_body(subject_tpl, recipient_obj)
                bdy = self.bulk_email_sender._personalize_email_body(body_tpl, recipient_obj)
                return {"success": True, "subject": sub, "body": bdy, "method": "Template"}
        except Exception as e:
            try:
                recipient_obj = RecipientData(**{k: recipient.get(k, "") for k in ["name", "email", "description"]})
                sub = self.bulk_email_sender._personalize_email_body(bulk_details.get("subject", ""), recipient_obj)
                bdy = self.bulk_email_sender._personalize_email_body(bulk_details.get("body_template", ""), recipient_obj)
                return {"success": True, "subject": sub, "body": bdy, "method": "Template (AI Failed)", "ai_error": str(e)}
            except Exception as e2:
                return {"success": False, "error": f"Failed preview: {str(e2)}"}
