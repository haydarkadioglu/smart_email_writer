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

You have access to the user's profile details under "User Profile / Identity". If the user asks about who they are, their background, or their experience, or asks you to write an email on their behalf, you MUST use their profile context to answer them accurately and personalize the content. Do NOT say you don't have information about them, as the profile is provided in the prompt.
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
                if extras:
                    profile_context = (
                        "User Profile / Identity (This is the profile of the user you are talking to and writing emails for):\n"
                        + "\n".join(extras)
                        + "\n\n"
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

    def chat_generate_user_summary(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a summary of the user based on the entire chat conversation history,
        and return it to be saved/edited in the 'About Me' field.
        """
        try:
            # Load all sessions and combine messages to get context about the user
            sessions = self.chat_store._load()
            if not sessions:
                return {"success": False, "error": "No chat sessions found. Start chatting first!"}

            # Gather up to 50 latest messages across all sessions to extract user background
            messages_text = ""
            count = 0
            for session in sessions:
                for msg in session.get("messages", []):
                    role_label = "User" if msg["role"] == "user" else "Assistant"
                    messages_text = f"{role_label}: {msg['content']}\n\n" + messages_text
                    count += 1
                    if count >= 50:
                        break
                if count >= 50:
                    break

            if not messages_text.strip():
                return {"success": False, "error": "Chat history is empty. Talk to the AI first!"}

            prompt = (
                "Based on the following chat conversation, extract key information about the user "
                "(their profession, company, skills, background, projects, or email writing preferences they mentioned). "
                "Write a concise, professional first-person summary ('I am...') of the user's profile/background "
                "in Turkish (or the primary language they chat in). "
                "This summary will help the AI personalize future emails. "
                "Return ONLY the summary text (max 3-4 sentences). Do NOT wrap it in JSON, markdown, or explanation.\n\n"
                "Chat History:\n" + messages_text
            )

            settings = self.settings_store.load()
            provider   = settings.get("ai_provider", "gemini")
            model_name = settings.get(provider + "_model", "")

            def do_summarize(client, p, m):
                raw = client._call_raw(prompt)
                return raw.strip()

            summary = self._execute_with_fallback(provider, model_name, do_summarize)
            summary = summary.strip().strip("```").strip()
            
            return {"success": True, "summary": summary}
        except Exception as e:
            return {"success": False, "error": str(e)}
