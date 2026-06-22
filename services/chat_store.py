import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List


class ChatStore:
    """Persistent store for AI chat conversations (config/chat_history.json)."""

    MAX_SESSIONS = 50
    MAX_MESSAGES = 200

    def __init__(self, filepath: str = "config/chat_history.json") -> None:
        self.filepath = filepath
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self, sessions: List[Dict[str, Any]]) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)

    def load_sessions(self) -> List[Dict[str, Any]]:
        sessions = self._load()
        # Return summary (no messages) for listing
        return [
            {
                "id":         s["id"],
                "title":      s.get("title", "Untitled"),
                "created_at": s.get("created_at", ""),
                "updated_at": s.get("updated_at", ""),
                "msg_count":  len(s.get("messages", [])),
            }
            for s in sessions
        ]

    def create_session(self, title: str = "New Chat") -> Dict[str, Any]:
        sessions = self._load()
        session = {
            "id":         str(uuid.uuid4()),
            "title":      title,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "messages":   [],
        }
        sessions.insert(0, session)
        if len(sessions) > self.MAX_SESSIONS:
            sessions = sessions[:self.MAX_SESSIONS]
        self._save(sessions)
        return session

    def get_session(self, session_id: str) -> Dict[str, Any]:
        for s in self._load():
            if s["id"] == session_id:
                return s
        return {}

    def append_message(
        self,
        session_id: str,
        role: str,           # "user" | "assistant"
        content: str,
        extra: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        sessions = self._load()
        msg = {
            "id":        str(uuid.uuid4()),
            "role":      role,
            "content":   content,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **(extra or {}),
        }
        for s in sessions:
            if s["id"] == session_id:
                s.setdefault("messages", []).append(msg)
                s["updated_at"] = msg["timestamp"]
                # Auto-title from first user message
                if role == "user" and len(s["messages"]) == 1:
                    s["title"] = content[:60] + ("…" if len(content) > 60 else "")
                # Limit messages
                if len(s["messages"]) > self.MAX_MESSAGES:
                    s["messages"] = s["messages"][-self.MAX_MESSAGES:]
                break
        self._save(sessions)
        return msg

    def delete_session(self, session_id: str) -> bool:
        sessions = self._load()
        new = [s for s in sessions if s["id"] != session_id]
        if len(new) == len(sessions):
            return False
        self._save(new)
        return True

    def clear_all(self) -> None:
        self._save([])
