"""
Perplexity provider implementation.

This provider uses Perplexity's OpenAI-compatible API endpoint to
perform chat completions. It uses the OpenAI SDK with a custom base
URL and environment variable for the API key. Models are configured
similarly to those for OpenAI.
"""

import os
from typing import Any, Dict, List

from openai import OpenAI

from agent.models.base import BaseProvider, ChatResponse, ModelInfo, ProviderError


class PerplexityProvider(BaseProvider):
    """
    PerplexityProvider uses Perplexity's OpenAI-compatible Chat Completions API.
    """

    def __init__(
        self,
        name: str,
        api_key_env: str,
        base_url: str,
        models: Dict[str, ModelInfo],
    ) -> None:
        super().__init__(name=name)
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.models = models

    @classmethod
    def from_config(cls, name: str, cfg: Dict[str, Any]) -> "PerplexityProvider":
        api_key_env = cfg.get("api_key_env", "PERPLEXITY_API_KEY")
        base_url = cfg.get("base_url", "https://api.perplexity.ai")
        models_cfg = cfg.get("models", {})
        models: Dict[str, ModelInfo] = {}
        for model_key, mcfg in models_cfg.items():
            models[model_key] = ModelInfo(
                name=mcfg["name"],
                supports_tools=bool(mcfg.get("supports_tools", False)),
                supports_stream=bool(mcfg.get("supports_stream", True)),
                max_context_tokens=int(mcfg.get("max_context_tokens", 8192)),
            )
        provider = cls(
            name=name,
            api_key_env=api_key_env,
            base_url=base_url,
            models=models,
        )
        return provider

    def _client(self) -> OpenAI:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ProviderError(
                f"Environment variable '{self.api_key_env}' is not set for provider '{self.name}'."
            )
        # Use the OpenAI SDK with Perplexity's base_url
        client = OpenAI(api_key=api_key, base_url=self.base_url)
        return client

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
    ) -> ChatResponse:
        client = self._client()
        try:
            if stream:
                chunks: List[str] = []
                stream_resp = client.chat.completions.create(
                    model=model, messages=messages, stream=True
                )
                for chunk in stream_resp:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        chunks.append(delta.content)
                text = "".join(chunks)
                return ChatResponse(text=text, raw=None)
            resp = client.chat.completions.create(model=model, messages=messages)
            text = resp.choices[0].message.content or ""
            return ChatResponse(text=text, raw=resp)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Perplexity provider error: {exc}") from exc