import os
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
