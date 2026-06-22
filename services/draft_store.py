import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class DraftStore:
    """Persistent store for email drafts (config/drafts.json)."""

    def __init__(self, filepath: str = "config/drafts.json") -> None:
        self.filepath = filepath
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self, drafts: List[Dict[str, Any]]) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(drafts, f, ensure_ascii=False, indent=2)

    # ── Public API ──────────────────────────────────────────────────────────

    def load_all(self) -> List[Dict[str, Any]]:
        return self._load()

    def get(self, draft_id: str) -> Optional[Dict[str, Any]]:
        for d in self._load():
            if d.get("id") == draft_id:
                return d
        return None

    def create(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        source: str = "manual",   # "manual" | "chat" | "bulk"
    ) -> Dict[str, Any]:
        drafts = self._load()
        draft = {
            "id":          str(uuid.uuid4()),
            "created_at":  datetime.now().isoformat(timespec="seconds"),
            "updated_at":  datetime.now().isoformat(timespec="seconds"),
            "to":          to,
            "subject":     subject,
            "body":        body,
            "attachments": attachments or [],
            "source":      source,
        }
        drafts.insert(0, draft)
        if len(drafts) > 500:
            drafts = drafts[:500]
        self._save(drafts)
        return draft

    def update(self, draft_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        drafts = self._load()
        for i, d in enumerate(drafts):
            if d.get("id") == draft_id:
                drafts[i] = {**d, **updates, "updated_at": datetime.now().isoformat(timespec="seconds")}
                self._save(drafts)
                return drafts[i]
        return None

    def delete(self, draft_id: str) -> bool:
        drafts = self._load()
        new_drafts = [d for d in drafts if d.get("id") != draft_id]
        if len(new_drafts) == len(drafts):
            return False
        self._save(new_drafts)
        return True

    def clear(self) -> None:
        self._save([])
