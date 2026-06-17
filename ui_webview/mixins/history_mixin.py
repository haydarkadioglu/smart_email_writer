from typing import Dict, List, Any

class HistoryMixin:
    def get_history(self) -> List[Dict[str, Any]]:
        return self.history_store.load_all()

    def clear_history(self) -> List[Dict[str, Any]]:
        self.history_store.clear()
        return []
