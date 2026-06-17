"""Anthropic Claude client via OpenAI-compatible API."""
from clients.openai_compat_base import OpenAICompatClient


class ClaudeClient(OpenAICompatClient):
    base_url      = "https://api.anthropic.com/v1"
    provider_name = "Claude"
    default_model = "claude-3-5-haiku-20241022"

    MODELS = [
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ]

    def __init__(self, api_key: str = "", model_name: str = "") -> None:
        # Anthropic's OpenAI-compat endpoint needs the anthropic-version header.
        # The openai SDK lets us pass extra headers via http_client or default_headers.
        super().__init__(api_key=api_key, model_name=model_name)
        if self._configured and self._client:
            # Patch the default headers for Anthropic
            self._client.default_headers = {
                **self._client.default_headers,
                "anthropic-version": "2023-06-01",
                "x-api-key": api_key,
            }
