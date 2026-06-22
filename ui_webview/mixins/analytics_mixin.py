from typing import Dict, Any


class AnalyticsMixin:
    """Email analytics with period filtering and keyword categorization."""

    def get_analytics(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Return aggregated mail statistics filtered by period.
        payload: { "period": "week" | "month" | "last_month" | "all" }
        """
        try:
            from datetime import datetime as _dt, timedelta as _td

            period = (payload or {}).get("period", "all")
            now = _dt.now()
            end_cutoff = None

            if period == "week":
                cutoff = now - _td(days=7)
            elif period == "month":
                cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == "last_month":
                first_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if first_this.month == 1:
                    cutoff = first_this.replace(year=first_this.year - 1, month=12)
                else:
                    cutoff = first_this.replace(month=first_this.month - 1)
                end_cutoff = first_this
            else:
                cutoff = None

            history = self.history_store.load_all()

            def in_period(entry: Dict[str, Any]) -> bool:
                ts_str = entry.get("timestamp", "")
                try:
                    ts = _dt.fromisoformat(ts_str)
                except Exception:
                    return False
                if end_cutoff:
                    return cutoff <= ts < end_cutoff
                if cutoff:
                    return ts >= cutoff
                return True

            filtered = [e for e in history if in_period(e)]

            total       = len(filtered)
            sent_ok     = sum(1 for e in filtered if e.get("status") == "success")
            sent_failed = sum(1 for e in filtered if e.get("status") == "failed")

            categories = self._categorize_emails(filtered)
            daily      = self._daily_breakdown(filtered)

            return {
                "success":     True,
                "period":      period,
                "total":       total,
                "sent_ok":     sent_ok,
                "sent_failed": sent_failed,
                "categories":  categories,
                "daily":       daily,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Helpers ────────────────────────────────────────────────────────────

    CAT_KEYWORDS = {
        "Toplantı / Meeting":  ["meeting", "toplantı", "call", "görüşme", "schedule"],
        "Takip / Follow-up":   ["follow", "takip", "reminder", "hatırlatma"],
        "Satış / Sales":       ["satış", "sales", "teklif", "offer", "proposal", "fiyat"],
        "Tanışma / Intro":     ["tanışma", "intro", "introduce", "merhaba", "hello"],
        "Başvuru / Apply":     ["başvuru", "apply", "application", "cv", "resume", "iş"],
        "Teşekkür / Thanks":   ["teşekkür", "thanks", "thank you", "appreciate"],
        "Bilgi / Info":        ["bilgi", "info", "information", "update", "güncelleme"],
    }

    def _categorize_emails(self, entries) -> Dict[str, int]:
        categories: Dict[str, int] = {}
        for entry in entries:
            text = (entry.get("subject", "") + " " + entry.get("body", "")[:200]).lower()
            matched = False
            for cat, kws in self.CAT_KEYWORDS.items():
                if any(kw in text for kw in kws):
                    categories[cat] = categories.get(cat, 0) + 1
                    matched = True
                    break
            if not matched:
                categories["Diğer / Other"] = categories.get("Diğer / Other", 0) + 1
        return categories

    def _daily_breakdown(self, entries) -> Dict[str, int]:
        from datetime import datetime as _dt
        daily: Dict[str, int] = {}
        for entry in entries[-200:]:
            ts_str = entry.get("timestamp", "")
            try:
                day = _dt.fromisoformat(ts_str).strftime("%Y-%m-%d")
                daily[day] = daily.get(day, 0) + 1
            except Exception:
                pass
        return daily
