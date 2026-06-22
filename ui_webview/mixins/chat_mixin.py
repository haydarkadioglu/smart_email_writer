import json
from typing import Dict, Any, List


SYSTEM_PROMPT = """You are SmartMail AI, an expert email writing assistant.
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
          session_id   str   - existing session id
          message      str   - user message text
          save_as_draft bool - whether to auto-save generated drafts
        """
        try:
            session_id   = payload.get("session_id", "")
            user_message = payload.get("message", "").strip()
            save_as_draft = payload.get("save_as_draft", True)

            if not user_message:
                return {"success": False, "error": "Empty message"}

            settings = self.settings_store.load()
            provider   = settings.get("ai_provider", "gemini")
            model_name = settings.get(provider + "_model", "")
            profile    = self.profile_store.load()

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
                + "Conversation so far:\n"
                + history_text
                + f"User: {user_message}\n\nAssistant:"
            )

            ai_client = self._get_ai_client(provider, model_name)
            raw_response = ai_client._call_raw(full_prompt)
            self._log_usage(provider, model_name, full_prompt, raw_response)

            # ── Save user message ───────────────────────────────────────────
            self.chat_store.append_message(session_id, "user", user_message)

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
                    draft = self.draft_store.create(
                        to=email_data.get("to", ""),
                        subject=email_data.get("subject", ""),
                        body=email_data.get("body", ""),
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
