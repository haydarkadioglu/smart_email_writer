"""DeepSeek client (deepseek-chat, deepseek-reasoner)."""
from clients.openai_compat_base import OpenAICompatClient


class DeepSeekClient(OpenAICompatClient):
    base_url      = "https://api.deepseek.com/v1"
    provider_name = "DeepSeek"
    default_model = "deepseek-chat"

    MODELS = [
        "deepseek-chat",
        "deepseek-reasoner",
    ]
