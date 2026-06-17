"""OpenRouter client – routes to 100+ models via a single API key."""
from clients.openai_compat_base import OpenAICompatClient


class OpenRouterClient(OpenAICompatClient):
    base_url      = "https://openrouter.ai/api/v1"
    provider_name = "OpenRouter"
    default_model = "meta-llama/llama-3.1-8b-instruct:free"

    # Popular free/cheap models on OpenRouter
    MODELS = [
        "meta-llama/llama-3.1-8b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-3-27b-it:free",
        "deepseek/deepseek-chat-v3-0324:free",
        "mistralai/mistral-7b-instruct:free",
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "google/gemini-2.0-flash-exp:free",
        "x-ai/grok-3-mini-beta",
    ]

    def __init__(self, api_key: str = "", model_name: str = "") -> None:
        super().__init__(api_key=api_key, model_name=model_name)
        # OpenRouter recommends sending HTTP-Referer and X-Title headers
        if self._configured and self._client:
            self._client.default_headers = {
                **self._client.default_headers,
                "HTTP-Referer": "https://github.com/haydarkadioglu/smart_email_writer",
                "X-Title": "Smart Email Writer",
            }
