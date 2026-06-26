import json
from typing import Dict, Any, List


SYSTEM_PROMPT = """You are SEW AI, an expert email writing assistant.
You help users write, review and send professional emails.

When the user asks you to draft an email, respond with a JSON object ONLY (no markdown, no explanation outside JSON) in this exact format:
{
  "type": "draft",
  "emails": [
    {"to": "<recipient email or empty>", "subject": "<subject>", "body": "<email body>"},
    ...
  ],
  "message": "<brief confirmation message to show the user>"
}

When the user asks a general question or makes a request that is NOT about drafting an email, respond with:
{
  "type": "message",
  "message": "<your response>"
}

When the user asks you to prepare a list / batch of emails for multiple people, include multiple objects in the "emails" array.
Always write emails that are professional, personalised and concise.
"""


class ChatMixin:
    """AI Chat API methods exposed to the JS front-end."""

    # ── Session management ───────────────────────────────────────────────────

    def chat_get_sessions(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            return {"success": True, "sessions": self.chat_store.load_sessions()}
        except Exception as e:
            return {"success": False, "error": str(e), "sessions": []}

    def chat_new_session(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            session = self.chat_store.create_session()
            return {"success": True, "session": session}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def chat_get_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            session_id = payload.get("session_id", "")
            session = self.chat_store.get_session(session_id)
            return {"success": bool(session), "session": session}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def chat_delete_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            session_id = payload.get("session_id", "")
            deleted = self.chat_store.delete_session(session_id)
            return {"success": deleted}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Messaging ────────────────────────────────────────────────────────────

    def chat_send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a user message to the AI and get a response.
        Optionally save resulting draft(s) to DraftStore.

        payload:
          session_id      str  - existing session id
          message         str  - user message text
          save_as_draft   bool - whether to auto-save generated drafts
          attachment_path str  - optional path to attached file
        """
        try:
            session_id      = payload.get("session_id", "")
            user_message    = payload.get("message", "").strip()
            save_as_draft   = payload.get("save_as_draft", True)
            attachment_path = payload.get("attachment_path", "").strip()

            if not user_message and not attachment_path:
                return {"success": False, "error": "Empty message"}

            settings = self.settings_store.load()
            provider   = settings.get("ai_provider", "gemini")
            model_name = settings.get(provider + "_model", "")
            profile    = self.profile_store.load()

            # ── Read Attachment content for context ──────────────────────────
            file_context = ""
            if attachment_path:
                from pathlib import Path
                p = Path(attachment_path)
                if p.exists():
                    ext = p.suffix.lower()
                    try:
                        if ext in ['.pdf', '.docx', '.txt', '.md']:
                            file_text = self._extract_text(p, ext)
                            file_context = f"\n\n--- ATTACHED FILE CONTENT ({p.name}) ---\n{file_text[:8000]}\n--- END ATTACHED FILE ---\n"
                        elif ext in ['.csv', '.xlsx', '.xls']:
                            import pandas as pd
                            if ext == '.csv':
                                df = pd.read_csv(p)
                            else:
                                df = pd.read_excel(p)
                            df_str = df.head(50).to_string()
                            file_context = f"\n\n--- ATTACHED FILE CONTENT ({p.name}) ---\n{df_str}\n--- END ATTACHED FILE ---\n"
                    except Exception as fe:
                        file_context = f"\n\n[Error reading attached file {p.name}: {fe}]\n"

            # ── Build conversation context ──────────────────────────────────
            session = self.chat_store.get_session(session_id)
            messages: List[Dict[str, str]] = session.get("messages", [])

            # Build a single prompt with history injected
            history_text = ""
            for m in messages[-10:]:  # last 10 messages for context window
                role_label = "User" if m["role"] == "user" else "Assistant"
                history_text += f"{role_label}: {m['content']}\n\n"

            profile_context = ""
            if profile:
                profile_context = (
                    f"Sender profile: {profile.get('name','')} "
                    f"<{profile.get('email','')}>, "
                    f"{profile.get('role','')} at {profile.get('company','')}.\n"
                )

            full_prompt = (
                SYSTEM_PROMPT
                + "\n\n"
                + profile_context
                + file_context
                + "Conversation so far:\n"
                + history_text
                + f"User: {user_message}\n\nAssistant:"
            )

            def do_chat(client, p, m):
                raw = client._call_raw(full_prompt)
                self._log_usage(p, m, full_prompt, raw)
                return raw

            raw_response = self._execute_with_fallback(provider, model_name, do_chat)

            # ── Save user message ───────────────────────────────────────────
            saved_user_message = user_message
            if attachment_path:
                import os
                filename = os.path.basename(attachment_path)
                saved_user_message = f"📎 [Attached: {filename}]\n{user_message}"
            
            self.chat_store.append_message(session_id, "user", saved_user_message)

            # ── Parse AI response ───────────────────────────────────────────
            clean = raw_response.strip().strip("```json").strip("```").strip()
            try:
                parsed = json.loads(clean)
            except json.JSONDecodeError:
                # Plain text response — wrap it
                parsed = {"type": "message", "message": raw_response.strip()}

            msg_type = parsed.get("type", "message")
            assistant_content = parsed.get("message", raw_response.strip())
            draft_ids: List[str] = []

            if msg_type == "draft" and save_as_draft:
                for email_data in parsed.get("emails", []):
                    attachments = [attachment_path] if attachment_path else []
                    draft = self.draft_store.create(
                        to=email_data.get("to", ""),
                        subject=email_data.get("subject", ""),
                        body=email_data.get("body", ""),
                        attachments=attachments,
                        source="chat",
                    )
                    draft_ids.append(draft["id"])

            # ── Save assistant message ──────────────────────────────────────
            self.chat_store.append_message(
                session_id, "assistant", assistant_content,
                extra={"draft_ids": draft_ids} if draft_ids else {}
            )

            return {
                "success":    True,
                "type":       msg_type,
                "message":    assistant_content,
                "emails":     parsed.get("emails", []) if msg_type == "draft" else [],
                "draft_ids":  draft_ids,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
