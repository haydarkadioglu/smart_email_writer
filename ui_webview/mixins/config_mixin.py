import os
import json
from pathlib import Path
from typing import Dict, Any

from clients.openai_client import OpenAIClient
from clients.claude_client import ClaudeClient
from clients.deepseek_client import DeepSeekClient
from clients.openrouter_client import OpenRouterClient


class ConfigMixin:
    def get_config(self) -> Dict[str, Any]:
        settings = self.settings_store.load()
        return {
            "profile":  self.profile_store.load(),
            "settings": settings,

            # Model lists per provider
            "gemini_models":     ["gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
            "groq_models":       ["llama-3.1-70b-versatile", "llama-3.3-70b-specdec", "llama3-70b-8192", "mixtral-8x7b-32768"],
            "openai_models":     OpenAIClient.MODELS,
            "claude_models":     ClaudeClient.MODELS,
            "deepseek_models":   DeepSeekClient.MODELS,
            "openrouter_models": OpenRouterClient.MODELS,

            # Which API keys are present in the environment or settings
            "api_keys_configured": {
                "gemini":     bool(os.getenv("GEMINI_API_KEY") or settings.get("api_key_gemini")),
                "groq":       bool(os.getenv("GROQ_API_KEY") or settings.get("api_key_groq")),
                "openai":     bool(os.getenv("OPENAI_API_KEY") or settings.get("api_key_openai")),
                "claude":     bool(os.getenv("CLAUDE_API_KEY") or settings.get("api_key_claude")),
                "deepseek":   bool(os.getenv("DEEPSEEK_API_KEY") or settings.get("api_key_deepseek")),
                "openrouter": bool(os.getenv("OPENROUTER_API_KEY") or settings.get("api_key_openrouter")),
            },

            # Env hint values (pre-fill SMTP from env)
            "env_smtp_email":    os.getenv("SMTP_EMAIL", ""),
            "env_smtp_provider": os.getenv("SMTP_PROVIDER", "gmail"),
        }

    def save_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        self.profile_store.save(profile_data)
        return {"success": True, "profile": profile_data}

    def save_settings(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        self.settings_store.save(settings_data)
        return {"success": True, "settings": settings_data}

    def save_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if "profile" in payload:
            self.profile_store.save(payload["profile"])
        
        # Save other configuration keys to settings
        settings = self.settings_store.load()
        updated = False
        for k, v in payload.items():
            if k != "profile":
                settings[k] = v
                updated = True
        
        if updated:
            self.settings_store.save(settings)
            
        return {"success": True}

    def get_usage_stats(self) -> Dict[str, Any]:
        """Return aggregated AI token usage from config/usage_logs.json."""
        try:
            log_path = Path("config") / "usage_logs.json"
            if not log_path.exists():
                return {"success": True, "logs": [], "total_cost": 0.0, "total_tokens": 0}
            logs = json.loads(log_path.read_text(encoding="utf-8"))
            total_cost   = sum(e.get("cost_usd", 0) for e in logs)
            total_tokens = sum(e.get("tokens_in", 0) + e.get("tokens_out", 0) for e in logs)
            return {
                "success":      True,
                "logs":         list(reversed(logs[-50:])),  # last 50, newest first
                "total_cost":   round(total_cost, 6),
                "total_tokens": total_tokens,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def clear_usage_logs(self) -> Dict[str, Any]:
        """Delete all usage log entries."""
        try:
            log_path = Path("config") / "usage_logs.json"
            if log_path.exists():
                log_path.write_text("[]", encoding="utf-8")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── CV / Resume parsing ────────────────────────────────────────────────

    def parse_cv(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a CV/Resume file and extract profile fields using AI.
        payload: { "file_path": str }
        """
        try:
            file_path = payload.get("file_path", "")
            if not file_path:
                return {"success": False, "error": "No file path provided"}

            from pathlib import Path as _Path
            p = _Path(file_path)
            if not p.exists():
                return {"success": False, "error": "File not found"}

            ext = p.suffix.lower()
            text = ""

            if ext == ".pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(str(p)) as pdf:
                        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                except ImportError:
                    return {"success": False, "error": "pdfplumber not installed. Run: pip install pdfplumber"}
            elif ext in (".docx",):
                try:
                    import docx
                    doc = docx.Document(str(p))
                    text = "\n".join(para.text for para in doc.paragraphs)
                except ImportError:
                    return {"success": False, "error": "python-docx not installed. Run: pip install python-docx"}
            elif ext in (".txt", ".md"):
                text = p.read_text(encoding="utf-8", errors="ignore")
            else:
                return {"success": False, "error": f"Unsupported file type: {ext}"}

            if not text.strip():
                return {"success": False, "error": "Could not extract text from file"}

            # Use AI to extract structured profile info
            prompt = (
                "Extract profile information from the following CV/resume text. "
                "Return ONLY a JSON object (no markdown, no explanation) with these keys: "
                "name, email, phone, company, role, website, summary. "
                "Use empty string \"\" for any field not found.\n\n"
                "CV Text:\n" + text[:4000]  # Limit to avoid token overflow
            )

            settings = self.settings_store.load()
            provider   = settings.get("ai_provider", "gemini")
            model_name = settings.get(provider + "_model", "")

            ai_client = self._get_ai_client(provider, model_name)
            raw = ai_client._call_raw(prompt)
            raw = raw.strip().strip("```json").strip("```").strip()

            profile_data = json.loads(raw)
            return {"success": True, "profile": profile_data}

        except json.JSONDecodeError:
            return {"success": False, "error": "AI returned invalid JSON"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Analytics ──────────────────────────────────────────────────────────

    def get_analytics(self, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Return aggregated mail statistics filtered by period.
        payload: { "period": "week" | "month" | "last_month" | "all" }
        """
        try:
            from datetime import datetime as _dt, timedelta as _td
            import re as _re

            period = (payload or {}).get("period", "all")
            now = _dt.now()

            if period == "week":
                cutoff = now - _td(days=7)
            elif period == "month":
                cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == "last_month":
                first_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                # First day of last month
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
                if period == "last_month":
                    return cutoff <= ts < end_cutoff
                if cutoff:
                    return ts >= cutoff
                return True

            filtered = [e for e in history if in_period(e)]

            total       = len(filtered)
            sent_ok     = sum(1 for e in filtered if e.get("status") == "success")
            sent_failed = sum(1 for e in filtered if e.get("status") == "failed")

            # Simple category detection based on subject keywords
            categories: Dict[str, int] = {}
            CAT_KEYWORDS = {
                "Toplantı / Meeting":  ["meeting", "toplantı", "call", "görüşme", "schedule"],
                "Takip / Follow-up":   ["follow", "takip", "reminder", "hatırlatma"],
                "Satış / Sales":       ["satış", "sales", "teklif", "offer", "proposal", "fiyat"],
                "Tanışma / Intro":     ["tanışma", "intro", "introduce", "merhaba", "hello"],
                "Başvuru / Apply":     ["başvuru", "apply", "application", "cv", "resume", "iş"],
                "Teşekkür / Thanks":   ["teşekkür", "thanks", "thank you", "appreciate"],
                "Bilgi / Info":        ["bilgi", "info", "information", "update", "güncelleme"],
            }
            for entry in filtered:
                subj = (entry.get("subject", "") + " " + entry.get("body", "")[:200]).lower()
                matched = False
                for cat, kws in CAT_KEYWORDS.items():
                    if any(kw in subj for kw in kws):
                        categories[cat] = categories.get(cat, 0) + 1
                        matched = True
                        break
                if not matched:
                    categories["Diğer / Other"] = categories.get("Diğer / Other", 0) + 1

            # Daily breakdown (last 30 days max)
            daily: Dict[str, int] = {}
            for entry in filtered[-200:]:
                ts_str = entry.get("timestamp", "")
                try:
                    day = _dt.fromisoformat(ts_str).strftime("%Y-%m-%d")
                    daily[day] = daily.get(day, 0) + 1
                except Exception:
                    pass

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

