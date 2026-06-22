import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any

from clients.gemini_client import GeminiClient
from clients.groq_client import GroqClient
from clients.openai_client import OpenAIClient
from clients.claude_client import ClaudeClient
from clients.deepseek_client import DeepSeekClient
from clients.openrouter_client import OpenRouterClient


class AiMixin:
    """AI provider selection, email generation/refinement and usage logging."""

    def _get_ai_client(self, provider: str, model_name: str):
        """Return the appropriate AI client for the given provider string."""
        p = provider.lower()
        settings = self.settings_store.load()

        def get_key(provider_name: str, env_var: str) -> str:
            val = settings.get(f"api_key_{provider_name}", "")
            if not val:
                val = os.getenv(env_var, "")
            return val

        if p == "groq":
            return GroqClient(api_key=get_key("groq", "GROQ_API_KEY"), model_name=model_name)
        elif p == "openai":
            return OpenAIClient(api_key=get_key("openai", "OPENAI_API_KEY"), model_name=model_name)
        elif p == "claude":
            return ClaudeClient(api_key=get_key("claude", "CLAUDE_API_KEY"), model_name=model_name)
        elif p == "deepseek":
            return DeepSeekClient(api_key=get_key("deepseek", "DEEPSEEK_API_KEY"), model_name=model_name)
        elif p == "openrouter":
            return OpenRouterClient(api_key=get_key("openrouter", "OPENROUTER_API_KEY"), model_name=model_name)
        else:  # default: gemini
            return GeminiClient(api_key=get_key("gemini", "GEMINI_API_KEY"), model_name=model_name)

    def _log_usage(self, provider: str, model: str, prompt_text: str, response_text: str):
        """Estimate token usage and append to config/usage_logs.json."""
        try:
            tokens_in  = max(1, len(prompt_text) // 4)
            tokens_out = max(1, len(response_text) // 4)
            cost_map = {
                "gemini":     (0.0000375, 0.00015),
                "groq":       (0.00005,   0.0001),
                "openai":     (0.005,     0.015),
                "claude":     (0.003,     0.015),
                "deepseek":   (0.00014,   0.00028),
                "openrouter": (0.001,     0.002),
            }
            in_rate, out_rate = cost_map.get(provider.lower(), (0.001, 0.002))
            cost_usd = (tokens_in / 1000) * in_rate + (tokens_out / 1000) * out_rate

            log_path = Path("config") / "usage_logs.json"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                logs = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
            except Exception:
                logs = []
            logs.append({
                "ts":         datetime.datetime.now().isoformat(timespec="seconds"),
                "provider":   provider,
                "model":      model,
                "tokens_in":  tokens_in,
                "tokens_out": tokens_out,
                "cost_usd":   round(cost_usd, 6),
            })
            log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass  # Never crash the main flow for logging

    def analyze_email(self, subject: str, body: str, language: str = "English") -> Dict[str, Any]:
        try:
            return self.spam_analyzer.analyze(subject, body, language)
        except Exception as e:
            return {"error": str(e)}

    def analyze_email_tone(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Use the active AI provider to analyse tone of an email draft."""
        try:
            provider   = payload.get("ai_provider", "gemini")
            model_name = payload.get("model", "")
            body       = payload.get("body", "")
            if not body.strip():
                return {"success": False, "error": "Email body is empty."}

            prompt = (
                "Analyze the tone of this email and return ONLY valid JSON (no markdown, no explanation) "
                "with these exact keys: formality (0-100), friendliness (0-100), urgency (0-100), "
                "clarity (0-100), advice (a short 1-sentence tip to improve the email).\n\nEmail:\n" + body
            )

            ai_client = self._get_ai_client(provider, model_name)
            raw = ai_client._call_raw(prompt)
            raw = raw.strip().strip("```json").strip("```").strip()
            data = json.loads(raw)
            self._log_usage(provider, model_name, prompt + body, raw)
            return {"success": True, "data": data}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"AI returned non-JSON response: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            provider           = payload.get("ai_provider", "gemini")
            model_name         = payload.get("model", "")
            purpose            = payload.get("purpose", "")
            recipient_name     = payload.get("receiver", "")
            company            = payload.get("company", "")
            tone               = payload.get("tone", "Professional")
            language           = payload.get("language", "Turkish")
            additional_context = payload.get("additional_context", "")
            email_length       = payload.get("email_length", "Medium (3-4 paragraphs)")

            if company:
                additional_context = f"Company: {company}\n{additional_context}"

            ai_client = self._get_ai_client(provider, model_name)
            profile   = self.profile_store.load()
            res = ai_client.generate_email(
                purpose=purpose,
                recipient_name=recipient_name,
                tone=tone,
                language=language,
                additional_context=additional_context,
                profile=profile,
                email_length=email_length
            )
            self._log_usage(provider, model_name, purpose, res.body)
            return {"success": True, "subject": res.subject, "email": res.body}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def refine_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            provider    = payload.get("ai_provider", "gemini")
            model_name  = payload.get("model", "")
            body        = payload.get("current_email", "")
            instruction = payload.get("instruction", "")
            tone        = payload.get("tone", "Professional")
            language    = payload.get("language", "Turkish")

            ai_client = self._get_ai_client(provider, model_name)
            profile   = self.profile_store.load()
            res = ai_client.refine_email(
                subject="",
                body=body,
                instruction=instruction,
                tone=tone,
                language=language,
                profile=profile
            )
            self._log_usage(provider, model_name, instruction + body, res.body)
            return {"success": True, "subject": res.subject, "email": res.body}
        except Exception as e:
            return {"success": False, "error": str(e)}
