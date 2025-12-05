"""
Tool plugin system.

Tools implement specific capabilities accessible by the agent, such
as performing web searches, fetching web pages, reading and writing
files, and executing limited shell commands. Tools are registered via
the `ToolRegistry` and made available to the model in the system prompt.
"""

__all__ = [
    "base",
    "web",
    "files",
    "shell",
]