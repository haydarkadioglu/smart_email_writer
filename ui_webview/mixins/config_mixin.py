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

            # Which API keys are present in the environment
            "api_keys_configured": {
                "gemini":     bool(os.getenv("GEMINI_API_KEY")),
                "groq":       bool(os.getenv("GROQ_API_KEY")),
                "openai":     bool(os.getenv("OPENAI_API_KEY")),
                "claude":     bool(os.getenv("CLAUDE_API_KEY")),
                "deepseek":   bool(os.getenv("DEEPSEEK_API_KEY")),
                "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
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
