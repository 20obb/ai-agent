"""
Anthropic provider implementation.

This provider wraps the Claude API via the official `anthropic` SDK.
It translates OpenAI-style chat messages into the format expected by
Anthropic's Claude models and collects their responses into a string.
"""

import os
from typing import Any, Dict, List

import anthropic

from agent.models.base import BaseProvider, ChatResponse, ModelInfo, ProviderError


class AnthropicProvider(BaseProvider):
    """
    AnthropicProvider wraps the Claude messages API via the official anthropic SDK.
    """

    def __init__(
        self,
        name: str,
        api_key_env: str,
        models: Dict[str, ModelInfo],
    ) -> None:
        super().__init__(name=name)
        self.api_key_env = api_key_env
        self.models = models

    @classmethod
    def from_config(cls, name: str, cfg: Dict[str, Any]) -> "AnthropicProvider":
        api_key_env = cfg.get("api_key_env", "ANTHROPIC_API_KEY")
        models_cfg = cfg.get("models", {})
        models: Dict[str, ModelInfo] = {}
        for model_key, mcfg in models_cfg.items():
            models[model_key] = ModelInfo(
                name=mcfg["name"],
                supports_tools=bool(mcfg.get("supports_tools", False)),
                supports_stream=bool(mcfg.get("supports_stream", True)),
                max_context_tokens=int(mcfg.get("max_context_tokens", 200000)),
            )
        provider = cls(name=name, api_key_env=api_key_env, models=models)
        return provider

    def _client(self) -> anthropic.Anthropic:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ProviderError(
                f"Environment variable '{self.api_key_env}' is not set for provider '{self.name}'."
            )
        client = anthropic.Anthropic(api_key=api_key)
        return client

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
    ) -> ChatResponse:
        client = self._client()
        # Convert OpenAI chat format to Anthropic format
        system_prompt = ""
        converted: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_prompt += content + "\n"
            elif role == "user":
                converted.append({"role": "user", "content": content})
            elif role == "assistant":
                converted.append({"role": "assistant", "content": content})
            else:
                converted.append({"role": "user", "content": content})
        try:
            if stream:
                chunks: List[str] = []
                stream_resp = client.messages.create(
                    model=model,
                    system=system_prompt,
                    messages=converted,
                    max_tokens=2048,
                    stream=True,
                )
                for event in stream_resp:
                    if event.type == "content_block_delta":
                        for c in event.delta.get("text", ""):
                            chunks.append(c)
                text = "".join(chunks)
                return ChatResponse(text=text, raw=None)
            resp = client.messages.create(
                model=model,
                system=system_prompt,
                messages=converted,
                max_tokens=2048,
                stream=False,
            )
            parts = []
            for block in resp.content:
                if getattr(block, "type", "") == "text":
                    parts.append(block.text)
            text = "\n".join(parts)
            return ChatResponse(text=text, raw=resp)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Anthropic provider error: {exc}") from exc