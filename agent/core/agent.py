"""
High-level agent implementations.

Defines:
- AskAgent: simple question-answering agent (no tools).
- ToolAgent: tool-using agent that expects JSON responses from the model
  to decide whether to call tools or return a final answer.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from agent.core.router import ModelRouter
from agent.core.prompts import PromptManager
from agent.models.base import ChatResponse
from agent.tools.base import ToolRegistry


class AskAgent:
    """
    Simple Q&A agent using a single model without tools.
    """

    def __init__(
        self,
        router: ModelRouter,
        prompts: PromptManager,
        provider_name: str,
        model_name: str,
    ) -> None:
        self.router = router
        self.prompts = prompts
        self.provider_name = provider_name
        self.model_name = model_name

    def ask(self, question: str) -> str:
        """
        Send a single question to the model and return the answer text.
        """
        system_prompt = self.prompts.get_ask_system_prompt()
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        response: ChatResponse = self.router.chat(
            provider_name=self.provider_name,
            model_name=self.model_name,
            messages=messages,
            stream=False,
        )
        return response.text


class ToolAgent:
    """
    Tool-using agent.

    The model is expected to:
    - Receive a system prompt describing available tools and JSON format.
    - Return JSON either requesting a tool call or providing a final answer.

    JSON formats:

    1) Tool call:
       {
         "tool": "tool_name",
         "tool_input": { ... }
       }

    2) Final answer (no more tool calls):
       {
         "tool": null,
         "final_answer": "..."
       }
    """

    def __init__(
        self,
        router: ModelRouter,
        prompts: PromptManager,
        tools: ToolRegistry,
        provider_name: str,
        model_name: str,
        max_steps: int = 4,
    ) -> None:
        self.router = router
        self.prompts = prompts
        self.tools = tools
        self.provider_name = provider_name
        self.model_name = model_name
        self.max_steps = max_steps

    def _build_tool_descriptions(self) -> str:
        """
        Build a human-readable description of available tools.

        This implementation is defensive and works with different
        ToolRegistry implementations:
        - If the registry has a `.tools` dict attribute, use it.
        - If it has a `.list_tools()` method, use that.
        - Otherwise, return an empty string.
        """
        lines: List[str] = []

        tools_iter = None
        if hasattr(self.tools, "tools"):
            tools_attr = getattr(self.tools, "tools")
            try:
                tools_iter = tools_attr.values()
            except Exception:  # noqa: BLE001
                tools_iter = None

        if tools_iter is None and hasattr(self.tools, "list_tools"):
            try:
                tools_iter = self.tools.list_tools()
            except Exception:  # noqa: BLE001
                tools_iter = None

        if tools_iter is None:
            return ""

        for tool in tools_iter:
            lines.append(f"- {tool.name}: {tool.description}")

        return "\n".join(lines)

    def run_task(self, task: str) -> str:
        """
        Run a task using the tool-enabled agent loop.

        Conversation pattern (roles) is kept compatible with providers
        like Perplexity that require user/assistant alternation:

        - One or more system messages at the top.
        - Then: user, assistant, user, assistant, ...
        """
        system_prompt = (
            self.prompts.get_agent_system_prompt()
            + "\n\nAvailable tools:\n"
            + self._build_tool_descriptions()
        )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ]

        invalid_json_attempts = 0

        for _ in range(self.max_steps):
            # Call the model with the current conversation
            response: ChatResponse = self.router.chat(
                provider_name=self.provider_name,
                model_name=self.model_name,
                messages=messages,
                stream=False,
            )

            # DEBUG: show raw assistant response from the model
            #print("\n[DEBUG assistant raw]:")
            #print(response.text)
            #print("----------\n")

            # Record the raw assistant message in the history
            messages.append({"role": "assistant", "content": response.text})

            raw = response.text.strip()
            raw_for_json = raw

            # If the model wrapped JSON in Markdown code fences, strip them
            if raw_for_json.startswith("```"):
                lines = raw_for_json.splitlines()

                # Drop first line if it's ``` or ```json
                if lines and lines[0].lstrip().startswith("```"):
                    lines = lines[1:]

                # Drop last line if it's ```
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]

                raw_for_json = "\n".join(lines).strip()

            # Try to parse JSON
            try:
                parsed = json.loads(raw_for_json)
            except json.JSONDecodeError:
                invalid_json_attempts += 1
                if invalid_json_attempts >= 2:
                    # Give up after 2 bad attempts, return raw text
                    return raw

                # Ask the model again, explicitly reminding the JSON format
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous message was not valid JSON. "
                            "You MUST respond with JSON ONLY as described in the system prompt. "
                            "Do not include any extra text."
                        ),
                    }
                )
                continue

            # If parsed is not a dict, just return raw text
            if not isinstance(parsed, Dict):
                return raw

            # If there is no 'tool' key at all, treat this as a final-ish answer
            if "tool" not in parsed:
                if "final_answer" in parsed and parsed["final_answer"]:
                    return str(parsed["final_answer"])
                if "error" in parsed:
                    return str(parsed["error"])
                return raw

            tool_name = parsed.get("tool")

            # If tool is null => final answer is expected
            if tool_name is None:
                final_answer = parsed.get("final_answer")
                if final_answer:
                    return str(final_answer)
                # final_answer is missing or empty => just return raw text
                return raw

            # Otherwise we have a tool call
            tool_input = parsed.get("tool_input", {}) or {}

            tool = self.tools.get_tool(tool_name)
            if tool is None:
                tool_error = f"Tool '{tool_name}' is not available."
                messages.append({"role": "user", "content": tool_error})
                continue

            try:
                tool_result = tool.run(tool_input)
            except Exception as exc:  # noqa: BLE001
                tool_result = f"Tool '{tool_name}' raised an error: {exc}"

            # Add tool result as a user message so the next model call sees it
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Result from tool '{tool_name}' with input {tool_input}:\n"
                        f"{tool_result}"
                    ),
                }
            )

        return "Maximum tool-calling steps reached without a final answer."
