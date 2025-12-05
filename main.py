from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, Tuple

from dotenv import load_dotenv

from agent.config import load_app_config
from agent.core.agent import AskAgent, ToolAgent
from agent.core.prompts import PromptManager
from agent.core.router import ModelRouter
from agent.models.base import ModelRegistry
from agent.models.openai_provider import OpenAIProvider
from agent.models.perplexity_provider import PerplexityProvider
from agent.models.anthropic_provider import AnthropicProvider
from agent.tools.base import ToolRegistry

# Adjust these imports if your tool modules use different paths/names
from agent.tools.shell import ShellCommandTool
from agent.tools.files import ReadFileTool, WriteFileTool
from agent.tools.web import WebSearchTool, WebFetchTool


# --------------------------------------------------------------------------------------
# Model / Tool registry builders
# --------------------------------------------------------------------------------------


def build_model_registry(cfg: Dict[str, Any]) -> ModelRegistry:
    """
    Build and register all configured model providers and models.

    Providers must specify whether they are enabled and supply the
    necessary configuration (API key environment variable, base URL,
    and list of models). Each model entry must include at least a
    `name` key corresponding to the provider's model identifier.
    """
    registry = ModelRegistry()
    providers_cfg = cfg.get("providers", {})

    # OpenAI provider
    if providers_cfg.get("openai", {}).get("enabled", False):
        registry.register_provider(
            OpenAIProvider.from_config("openai", providers_cfg["openai"])
        )

    # Perplexity provider (OpenAI-compatible)
    if providers_cfg.get("perplexity", {}).get("enabled", False):
        registry.register_provider(
            PerplexityProvider.from_config("perplexity", providers_cfg["perplexity"])
        )

    # Anthropic provider
    if providers_cfg.get("anthropic", {}).get("enabled", False):
        registry.register_provider(
            AnthropicProvider.from_config("anthropic", providers_cfg["anthropic"])
        )

    # 🔴 هنا كانت المشكلة: لازم نسجّل الموديلات داخل ModelRegistry
    for provider_name, provider_cfg in providers_cfg.items():
        models_cfg = provider_cfg.get("models", {})
        for model_key, mcfg in models_cfg.items():
            # تأكد أن الـ provider مسجل أصلاً (مثلاً openai ممكن يكون disabled)
            provider = registry.providers.get(provider_name)
            if provider is None:
                continue
            # تأكد أن الموديل موجود داخل provider.models
            if model_key not in provider.models:
                continue
            registry.register_model(
                provider_name=provider_name,
                model_key=model_key,
                model_info=provider.models[model_key],
            )

    return registry



def build_tool_registry(cfg: Dict[str, Any]) -> ToolRegistry:
    """
    Build the tool registry from config.yaml.

    Tools are registered only if they are enabled in the `tools:` section.
    This version assumes each Tool class exposes:

        @classmethod
        def from_config(cls, config: dict) -> "Tool":
            ...

    i.e. only a single explicit argument (config), plus the implicit `cls`.
    """
    tools_cfg = cfg.get("tools", {})
    registry = ToolRegistry()

    # Shell command tool
    shell_cfg = tools_cfg.get("shell")
    if shell_cfg and shell_cfg.get("enabled", False):
        registry.register_tool(ShellCommandTool.from_config(shell_cfg))

    # File tools
    read_cfg = tools_cfg.get("read_file")
    if read_cfg and read_cfg.get("enabled", False):
        registry.register_tool(ReadFileTool.from_config(read_cfg))

    write_cfg = tools_cfg.get("write_file")
    if write_cfg and write_cfg.get("enabled", False):
        registry.register_tool(WriteFileTool.from_config(write_cfg))

    # Web tools (optional)
    web_search_cfg = tools_cfg.get("web_search")
    if web_search_cfg and web_search_cfg.get("enabled", False):
        registry.register_tool(WebSearchTool.from_config(web_search_cfg))

    web_fetch_cfg = tools_cfg.get("web_fetch")
    if web_fetch_cfg and web_fetch_cfg.get("enabled", False):
        registry.register_tool(WebFetchTool.from_config(web_fetch_cfg))

    return registry


def build_router_and_prompts(cfg: Dict[str, Any]) -> Tuple[ModelRouter, PromptManager, ModelRegistry]:
    """
    Build ModelRouter, PromptManager, and ModelRegistry from raw config dict.
    """
    model_registry = build_model_registry(cfg)
    router = ModelRouter(model_registry)
    prompts = PromptManager(cfg.get("prompts", {}))
    return router, prompts, model_registry


# --------------------------------------------------------------------------------------
# Interactive chat loop
# --------------------------------------------------------------------------------------


def interactive_chat(
    mode: str,
    router: ModelRouter,
    prompts: PromptManager,
    tools: ToolRegistry,
    provider_name: str,
    model_name: str,
    max_steps: int = 4,
) -> None:
    """
    Simple terminal chat loop.

    mode:
      - "ask":   normal Q&A mode, no tools.
      - "agent": tool-using mode (shell, files, etc.).

    The session keeps running until:
      - user types /exit or /quit
      - or presses Ctrl+C.
    """
    if mode == "ask":
        agent = AskAgent(
            router=router,
            prompts=prompts,
            provider_name=provider_name,
            model_name=model_name,
        )
    else:
        agent = ToolAgent(
            router=router,
            prompts=prompts,
            tools=tools,
            provider_name=provider_name,
            model_name=model_name,
            max_steps=max_steps,
        )

    print(f"\n[Interactive chat started in {mode.upper()} mode]")
    print("Provider:", provider_name)
    print("Model   :", model_name)
    print("Type /exit or press Ctrl+C to end the session.\n")

    while True:
        try:
            user_input = input("You> ").strip()
            if not user_input:
                continue

            if user_input.lower() in {"/exit", "/quit"}:
                print("Bye 👋")
                break

            if mode == "ask":
                reply = agent.ask(user_input)
            else:
                reply = agent.run_task(user_input)

            print("Assistant> ", reply)
        except KeyboardInterrupt:
            print("\n[Session interrupted by user, exiting chat]")
            break


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-provider LLM agent (ask mode, agent mode, and interactive chat)."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to config.yaml (or toml) file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ask: single-turn Q&A
    ask_parser = subparsers.add_parser(
        "ask", help="Single question (no tools)."
    )
    ask_parser.add_argument(
        "--provider",
        required=True,
        help="Provider name (e.g., perplexity, openai, anthropic).",
    )
    ask_parser.add_argument(
        "--model",
        required=True,
        help="Model key as defined in config.yaml for the chosen provider.",
    )
    ask_parser.add_argument(
        "question",
        help="User question to send to the model.",
    )

    # agent: single task with tools
    agent_parser = subparsers.add_parser(
        "agent", help="Run a single agent task (with tools)."
    )
    agent_parser.add_argument(
        "--provider",
        required=True,
        help="Provider name (e.g., perplexity, openai, anthropic).",
    )
    agent_parser.add_argument(
        "--model",
        required=True,
        help="Model key as defined in config.yaml for the chosen provider.",
    )
    agent_parser.add_argument(
        "--max-steps",
        type=int,
        default=4,
        help="Maximum tool-calling steps for the agent.",
    )
    agent_parser.add_argument(
        "task",
        help="Task description for the agent (e.g., instructions including tool usage).",
    )

    # chat: interactive loop (ask or agent mode)
    chat_parser = subparsers.add_parser(
        "chat", help="Interactive chat session (ask or agent mode)."
    )
    chat_parser.add_argument(
        "--mode",
        choices=["ask", "agent"],
        default="ask",
        help="Chat mode: 'ask' for normal Q&A, 'agent' for tool-using agent.",
    )
    chat_parser.add_argument(
        "--provider",
        required=True,
        help="Provider name (e.g., perplexity, openai, anthropic).",
    )
    chat_parser.add_argument(
        "--model",
        required=True,
        help="Model key as defined in config.yaml for the chosen provider.",
    )
    chat_parser.add_argument(
        "--max-steps",
        type=int,
        default=4,
        help="Maximum tool-calling steps in agent mode.",
    )

    return parser.parse_args(argv)


# --------------------------------------------------------------------------------------
# main()
# --------------------------------------------------------------------------------------


def main() -> None:
    # Load environment variables from .env (if present)
    load_dotenv()

    args = parse_args(sys.argv[1:])

    # Load config from YAML/TOML
    config = load_app_config(args.config)

    # Build core components
    router, prompts, model_registry = build_router_and_prompts(config)
    tools = build_tool_registry(config)

    # Dispatch commands
    if args.command == "chat":
        interactive_chat(
            mode=args.mode,
            router=router,
            prompts=prompts,
            tools=tools,
            provider_name=args.provider,
            model_name=args.model,
            max_steps=args.max_steps,
        )
        return

    if args.command == "ask":
        ask_agent = AskAgent(
            router=router,
            prompts=prompts,
            provider_name=args.provider,
            model_name=args.model,
        )
        answer = ask_agent.ask(args.question)
        print(answer)
        return

    if args.command == "agent":
        tool_agent = ToolAgent(
            router=router,
            prompts=prompts,
            tools=tools,
            provider_name=args.provider,
            model_name=args.model,
            max_steps=args.max_steps,
        )
        result = tool_agent.run_task(args.task)
        print(result)
        return

    # Should never reach here
    raise SystemExit(f"Unknown command: {args.command!r}")


if __name__ == "__main__":
    main()
