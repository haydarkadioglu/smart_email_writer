import webview
from typing import Dict, Any, List


class DraftMixin:
    """API methods for managing email drafts exposed to the JS front-end."""

    # ── CRUD ────────────────────────────────────────────────────────────────

    def get_drafts(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            drafts = self.draft_store.load_all()
            return {"success": True, "drafts": drafts}
        except Exception as e:
            return {"success": False, "error": str(e), "drafts": []}

    def create_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            draft = self.draft_store.create(
                to=payload.get("to", ""),
                subject=payload.get("subject", ""),
                body=payload.get("body", ""),
                attachments=payload.get("attachments", []),
                source=payload.get("source", "manual"),
            )
            return {"success": True, "draft": draft}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            draft_id = payload.get("id")
            if not draft_id:
                return {"success": False, "error": "Missing draft id"}
            updates = {k: v for k, v in payload.items() if k != "id"}
            updated = self.draft_store.update(draft_id, updates)
            if updated is None:
                return {"success": False, "error": "Draft not found"}
            return {"success": True, "draft": updated}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            draft_id = payload.get("id")
            deleted = self.draft_store.delete(draft_id)
            return {"success": deleted, "error": "" if deleted else "Draft not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── File picker for attachments ─────────────────────────────────────────

    def pick_attachment(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Open a native file picker and return the selected paths."""
        try:
            if not self.window:
                return {"success": False, "error": "No window", "files": []}
            files = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=True,
                file_types=("All Files (*.*)",),
            )
            return {"success": True, "files": list(files) if files else []}
        except Exception as e:
            return {"success": False, "error": str(e), "files": []}

    # ── Send a draft via SMTP ───────────────────────────────────────────────

    def send_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve draft by id, merge with SMTP settings and send."""
        try:
            draft_id = payload.get("draft_id")
            draft = self.draft_store.get(draft_id) if draft_id else None
            if draft is None:
                return {"success": False, "error": "Draft not found"}

            settings = self.settings_store.load()
            smtp_payload = {
                "smtp_provider": settings.get("smtp_provider", "Gmail"),
                "smtp_email":    settings.get("smtp_email", ""),
                "smtp_password": settings.get("smtp_password", ""),
                "to_email":      draft["to"],
                "subject":       draft["subject"],
                "body":          draft["body"],
                "attachments":   draft.get("attachments", []),
                "log_id":        "draft",
            }
            result = self.send_email(smtp_payload)
            if result.get("success"):
                # Remove draft after successful send
                self.draft_store.delete(draft_id)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
