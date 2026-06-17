from typing import Dict, List, Any

class HistoryMixin:
    def get_history(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            history = self.history_store.load_all()
            if payload:
                limit = payload.get("limit")
                if limit and isinstance(limit, int):
                    history = history[:limit]
            return {"success": True, "history": history}
        except Exception as e:
            return {"success": False, "error": str(e), "history": []}

    def clear_history(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            self.history_store.clear()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
