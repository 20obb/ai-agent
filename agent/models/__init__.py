"""
Model provider implementations.

This package collects base types and helper classes in `base.py` and
concrete provider implementations for OpenAI, Perplexity (OpenAI-compatible),
and Anthropic. Adding a new provider involves creating a new module
that subclasses `BaseProvider`.
"""

__all__ = [
    "base",
    "openai_provider",
    "perplexity_provider",
    "anthropic_provider",
]