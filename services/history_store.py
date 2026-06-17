import json
import os
from datetime import datetime
from typing import Any, Dict, List


class HistoryStore:
    def __init__(self, filepath: str = "config/history.json") -> None:
        self.filepath = filepath
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def load_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_all(self, history: List[Dict[str, Any]]) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def append(
        self,
        provider: str,
        sender: str,
        recipient: str,
        subject: str,
        body: str,
        status: str = "success",
        error_message: str = "",
    ) -> Dict[str, Any]:
        history = self.load_all()
        entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "status": status,
            "error_message": error_message,
        }
        # Insert at the beginning to show newest first
        history.insert(0, entry)
        # Limit history to last 200 entries to save disk space and loading time
        if len(history) > 200:
            history = history[:200]
        self.save_all(history)
        return entry

    def clear(self) -> None:
        self.save_all([])
