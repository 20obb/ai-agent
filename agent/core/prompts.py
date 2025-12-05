"""
Prompt management.

This module provides a simple PromptManager class that reads prompt
configurations from the loaded YAML configuration and exposes them
to the agent logic. It supplies default values if prompts are not
specified.
"""

from typing import Dict


class PromptManager:
    """
    Store and access system prompts used by ask mode and tool-enabled mode.

    Prompts can be configured in the YAML file under the `prompts` key.
    """

    def __init__(self, prompts_cfg: Dict) -> None:
        self.prompts_cfg = prompts_cfg or {}

    def get_ask_system_prompt(self) -> str:
        """
        Retrieve the system prompt for simple ask mode.

        Returns:
            A string containing the system prompt.
        """
        return self.prompts_cfg.get(
            "ask_system",
            (
                "You are a helpful assistant. Answer the user's question clearly and "
                "concisely. Do not claim to execute actions or tools in this mode."
            ),
        )

    def get_agent_system_prompt(self) -> str:
        """
        Retrieve the system prompt for tool-enabled agent mode.

        Returns:
            A string containing the system prompt.
        """
        return self.prompts_cfg.get(
            "agent_system",
            (
                "You are a tool-using AI agent. You can call tools to browse the web, "
                "read and write files, and run commands in a safe, restricted way.\n\n"
                "You must always respond in JSON ONLY, with one of the following forms:\n\n"
                "1) To call a tool:\n"
                "{\n"
                '  "tool": "tool_name",\n'
                '  "tool_input": { ... }\n'
                "}\n\n"
                "2) To provide a final answer (no more tool calls):\n"
                "{\n"
                '  "tool": null,\n'
                '  "final_answer": "..."\n'
                "}\n\n"
                "Never include any non-JSON text in your response. Tool names and input "
                "must match the descriptions you are given."
            ),
        )