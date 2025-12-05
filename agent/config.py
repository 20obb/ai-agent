"""
Configuration loader for the AI agent system.

The configuration is stored in a YAML file. This module provides a
function to load that file into a Python dictionary. Sensitive values
like API keys are not stored in the YAML file; instead, they are
retrieved from environment variables as needed by the providers.
"""

import os
from typing import Any, Dict

import yaml


def load_app_config(path: str) -> Dict[str, Any]:
    """
    Load the application configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        A dictionary representing the configuration.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the top-level configuration is not a mapping.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError("Top-level configuration must be a mapping/dictionary.")

    return data