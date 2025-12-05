"""
Model routing logic.

The router is responsible for resolving which provider and model
should handle a given chat request. It delegates the actual API
requests to the provider classes in the models package.
"""

from typing import Any, Dict, List

from agent.models.base import ModelRegistry, ProviderError, ChatResponse


class ModelRouter:
    """
    ModelRouter dispatches chat requests to the appropriate provider
    and model based on the configuration of the model registry. It
    abstracts away the details of provider-specific API calls from
    higher-level agent logic.
    """

    def __init__(self, model_registry: ModelRegistry) -> None:
        self.model_registry = model_registry

    def chat(
        self,
        provider_name: str,
        model_name: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
    ) -> ChatResponse:
        """
        Forward a chat completion request to the chosen provider and model.

        Args:
            provider_name: The registered provider name.
            model_name: The registered model key under that provider.
            messages: A list of message dicts in OpenAI chat format.
            stream: Whether to request streaming responses.

        Returns:
            A ChatResponse object containing the response text and raw data.

        Raises:
            ProviderError: If the provider or model cannot be resolved or
                the API call fails.
        """
        provider, model_info = self.model_registry.resolve(provider_name, model_name)
        return provider.chat(model=model_info.name, messages=messages, stream=stream)