"""
Base types and registry for model providers.

Defines common classes and data structures that all model providers
implement, along with a registry to map provider names and models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class ChatResponse:
    """
    Normalized chat response returned by providers.

    The text attribute contains the plain response text. The raw
    attribute contains provider-specific response data for debugging
    or advanced use.
    """

    text: str
    raw: Any


class ProviderError(Exception):
    """Raised when a provider fails to execute a request."""


class BaseProvider:
    """
    Abstract base class for all LLM providers.

    Providers must implement the `chat` method. A classmethod
    `from_config` is used to construct provider instances from
    configuration dictionaries.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
    ) -> ChatResponse:
        raise NotImplementedError

    @classmethod
    def from_config(cls, name: str, cfg: Dict[str, Any]) -> "BaseProvider":
        raise NotImplementedError


@dataclass
class ModelInfo:
    """
    ModelInfo stores metadata about a model used by a provider.
    """

    name: str
    supports_tools: bool = False
    supports_stream: bool = True
    max_context_tokens: int = 8192


class ModelRegistry:
    """
    ModelRegistry keeps track of providers and their models.
    """

    def __init__(self) -> None:
        self.providers: Dict[str, BaseProvider] = {}
        self.models: Dict[Tuple[str, str], ModelInfo] = {}

    def register_provider(self, provider: BaseProvider) -> None:
        self.providers[provider.name] = provider

    def register_model(
        self,
        provider_name: str,
        model_key: str,
        model_info: ModelInfo,
    ) -> None:
        self.models[(provider_name, model_key)] = model_info

    def resolve(
        self, provider_name: str, model_key: str
    ) -> Tuple[BaseProvider, ModelInfo]:
        """
        Resolve a provider and model pair from registered names.
        """
        provider = self.providers.get(provider_name)
        if provider is None:
            raise ProviderError(f"Provider '{provider_name}' not registered.")
        model_info = self.models.get((provider_name, model_key))
        if model_info is None:
            raise ProviderError(
                f"Model '{model_key}' not registered for provider '{provider_name}'."
            )
        return provider, model_info