"""OpenAI client (GPT-4o, GPT-4o-mini, o1, etc.)"""
from clients.openai_compat_base import OpenAICompatClient


class OpenAIClient(OpenAICompatClient):
    base_url      = "https://api.openai.com/v1"
    provider_name = "OpenAI"
    default_model = "gpt-4o-mini"

    MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "o1-mini",
    ]
