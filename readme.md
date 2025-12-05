
````markdown
# Multi-Provider AI Agent (CLI + Agent + Chat)

A modular, security-aware AI Agent framework written in Python.

It lets you:

- Talk to multiple LLM providers (Perplexity, OpenAI, Anthropic, etc.).
- Run in three modes:
  - `ask` – simple Q&A (no tools, no side effects).
  - `agent` – single task with tools (shell, files, optional web tools).
  - `chat` – interactive terminal chat (ask or agent mode).
- Use tools in **agent mode** to:
  - Execute shell commands (e.g. `free -h`, `lscpu`, `ls`).
  - Read and write files (within configurable directories).
  - Optionally call external web search APIs (if you configure them).

> ⚠️ When tools are enabled with wide permissions, the agent can run real commands and modify real files on your machine.  
> Use this responsibly, ideally inside a VM or restricted environment.

---

## Table of Contents

- [Project Idea](#project-idea)
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
  - [.env example](#env-example)
  - [config.yaml structure](#configyaml-structure)
- [Usage](#usage)
  - [Ask mode (one-shot Q&A)](#ask-mode-one-shot-qa)
  - [Agent mode (single task with tools)](#agent-mode-single-task-with-tools)
  - [Chat mode (interactive session)](#chat-mode-interactive-session)
- [Tools & Permissions](#tools--permissions)
- [Security Notes](#security-notes)
- [Extending the Project](#extending-the-project)
  - [Adding a new provider / model](#adding-a-new-provider--model)
  - [Adding a new tool plugin](#adding-a-new-tool-plugin)
- [Project Structure](#project-structure)
- [License](#license)

---

## Project Idea

In simple terms:

> This project is a **command-line AI control center** where you can plug in different LLM providers (like Perplexity), choose a mode (simple chat or fully-powered agent), and optionally give the agent controlled access to your system (shell + files) through tools.

You can:

- Use it as a **normal chat assistant** (`ask` / `chat --mode ask`).
- Use it as a **system helper** that:
  - checks RAM/CPU via shell (`free -h`, `lscpu`, `top`),
  - reads log/config files,
  - writes or edits code files,
  all via `agent` mode.

All behavior is controlled by configuration files (`config.yaml`, `.env`) — not hard-coded.

---

## Features

- **Multi-provider support**
  - Perplexity (OpenAI-compatible HTTP API).
  - Optional: OpenAI, Anthropic.
  - Easy to extend with new providers.

- **Three operation modes**
  - `ask`: one question → one answer, **no tools**.
  - `agent`: single task with tools (shell/FS/web).
  - `chat`: interactive REPL-style session (ask or agent).

- **Tooling system**
  - `shell_command`: run shell commands.
  - `read_file`: read files under a configured root directory.
  - `write_file`: create/modify files under a configured root directory.
  - `web_search` / `web_fetch`: optional HTTP tools wired to your own search API.

- **Unified configuration**
  - Providers, models, tools, and prompts are all configured via `config.yaml`.
  - API keys loaded from environment variables or `.env` using `python-dotenv`.

- **Security-aware**
  - You explicitly enable/disable tools.
  - You configure:
    - `root_dir` for file tools,
    - `working_dir` and `allowed_commands` for shell tool.
  - Makes it easy to restrict the agent to a sandbox directory.

- **Clean, modular structure**
  - Core logic (routing, prompts, agents) is separated from:
    - providers,
    - tools,
    - configuration.

---

## Architecture Overview

At a high level, the project is built around a few core concepts:

### ModelRegistry

- Holds all enabled providers and their models.
- Allows resolving `(provider_name, model_key)` into:
  - a concrete provider object,
  - plus model metadata (name, context size, feature flags).

### ModelRouter

- Given:
  - provider name,
  - model key,
  - chat messages,
- It picks the correct provider and delegates the call:
  ```python
  provider.chat(model=model_info.name, messages=messages, stream=False) -> ChatResponse
````

### Provider classes (`agent/models/*.py`)

* Examples:

  * `OpenAIProvider`
  * `PerplexityProvider`
  * `AnthropicProvider`
* Each provider:

  * wraps its own HTTP API (OpenAI-style, Anthropic-style, etc.),
  * implements a unified `chat(...)` interface,
  * reads required configuration (base URL, API key env var, model list) from `config.yaml`.

### ToolRegistry (`agent/tools/base.py`)

* Stores each available tool instance:

  * `ShellCommandTool`
  * `ReadFileTool`
  * `WriteFileTool`
  * `WebSearchTool`
  * `WebFetchTool`
* Each tool is constructed from its own `from_config(config: dict)` and exposes a unified `run(tool_input: dict) -> str`.

### Agents (`agent/core/agent.py`)

There are two main agent types:

* **AskAgent**

  * Simple LLM assistant:

    * No tools,
    * Just system + user messages → response.

* **ToolAgent**

  * Tool-using LLM agent:

    * Uses a system prompt (`agent_system`) that describes available tools and JSON calling format.
    * Loop:

      1. Calls the model.
      2. If the model returns JSON requesting a tool:

         * Runs the tool.
         * Injects the tool result into the conversation.
      3. Repeats until:

         * The model returns a `final_answer`, or
         * The `max_steps` limit is reached.

### Prompts (`agent/core/prompts.py`)

* `ask_system`: system prompt for ask mode.
* `agent_system`: system prompt for tool-using agent; explains:

  * what tools exist,
  * how to call them via JSON,
  * how to return a final answer.

---

## Requirements

* **Python**: 3.10+ recommended (3.11/3.12 even better).
* **OS**:

  * Linux (primary target),
  * macOS and WSL should also work with shell tools.
* **Network**:

  * Internet access to reach the configured LLM APIs (Perplexity, etc.).
* **API keys**:

  * Perplexity API key is required when using Perplexity provider.

---

## Installation

### 1. Clone or download the repository

Either:

```bash
git clone https://github.com/20obb/ai-agent.git
cd ai-agent
```

Or download a ZIP from GitHub and extract it, then `cd` into the project directory.

> Replace `your-username` with your actual GitHub username.

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
# .venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

You configure the project using:

1. A `.env` file (for API keys and secrets).
2. A `config.yaml` file (for providers, models, tools, prompts).

Both live in the project root.

### .env example

Create a file named `.env`:

```env
# Perplexity (required if you use the Perplexity provider)
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: external search API for web_search tool
# SEARCH_API_ENDPOINT=https://your-search-api.example.com/search
# SEARCH_API_KEY=your-search-api-key-here
```

The project uses `python-dotenv` to load this automatically.

### config.yaml structure

Below is an example aligned with the current design of the repo:

```yaml
providers:
  openai:
    enabled: false
    api_key_env: OPENAI_API_KEY
    base_url: https://api.openai.com/v1
    models:
      gpt4o-mini:
        name: gpt-4o-mini
        supports_tools: true
        supports_stream: true
        max_context_tokens: 128000
      gpt4o:
        name: gpt-4o
        supports_tools: true
        supports_stream: true
        max_context_tokens: 128000

  perplexity:
    enabled: true
    api_key_env: PERPLEXITY_API_KEY
    base_url: https://api.perplexity.ai
    models:
      sonar-small:
        name: sonar                # or sonar-small if required by API docs
        supports_tools: false      # currently used in ask/chat without tools
        supports_stream: true
        max_context_tokens: 32768

      sonar-pro:
        name: sonar-pro
        supports_tools: false
        supports_stream: true
        max_context_tokens: 65536

      sonar-reasoning:
        name: sonar-reasoning
        supports_tools: false
        supports_stream: true
        max_context_tokens: 32768

      sonar-deep-research:
        name: sonar-deep-research
        supports_tools: false
        supports_stream: true
        max_context_tokens: 65536

  anthropic:
    enabled: false
    api_key_env: ANTHROPIC_API_KEY
    base_url: https://api.anthropic.com
    models:
      claude-3-haiku:
        name: claude-3-haiku-20240307
        supports_tools: true
        supports_stream: true
        max_context_tokens: 200000
      claude-3-sonnet:
        name: claude-3-sonnet-20240229
        supports_tools: true
        supports_stream: true
        max_context_tokens: 200000
      claude-3-opus:
        name: claude-3-opus-20240229
        supports_tools: true
        supports_stream: true
        max_context_tokens: 200000

tools:
  web_search:
    enabled: false
    # enable and configure endpoint_env / api_key_env if you plug in a search API

  web_fetch:
    enabled: false
    # enable if you implement an HTTP fetch tool

  read_file:
    enabled: true
    root_dir: /            # WARNING: full filesystem read access

  write_file:
    enabled: true
    root_dir: /            # WARNING: full filesystem write access

  shell:
    enabled: true
    working_dir: /
    allowed_commands: []   # [] means no restrictions, all commands allowed (dangerous)
    # default_timeout: 15  # optional

prompts:
  ask_system: >
    You are a helpful assistant. Answer the user's question clearly and concisely.
    Do not claim to browse the web or execute tools in this mode.
    You are allowed to use your own internal knowledge and reasoning, but you do not
    have direct access to the user's filesystem or shell in ask mode.

  agent_system: >
    You are a tool-using AI agent running on the user's Linux machine.

    You have access to these tools:
    - shell_command: execute shell commands on the user's system
      (with the same permissions as the current OS user).
    - read_file: read arbitrary files from the filesystem within the configured root_dir.
    - write_file: create or modify files on the filesystem within the configured root_dir.

    When you decide that a tool is needed, you SHOULD respond with JSON ONLY,
    in one of these forms:

    1) To call a tool:
       {
         "tool": "shell_command",
         "tool_input": {
           "command": "free -h",
           "timeout": 15
         }
       }

    2) To provide a final answer (no more tool calls):
       {
         "tool": null,
         "final_answer": "your explanation here"
       }

    If the user just wants a simple explanation and no tools are needed,
    you may answer in natural language instead of JSON.
```

Key points:

* The value passed to `--model` on CLI (e.g. `sonar-pro`) must match the **model key** under `models:` (here `sonar-pro`), not the `name:` field.
* The `name:` is what gets sent to the provider’s API.

---

## Usage

All commands assume:

* You are in the project root (where `main.py` lives).
* Your virtual environment is activated.
* `.env` and `config.yaml` are properly set up.

### Ask mode (one-shot Q&A)

This is the simplest and safest mode: no tools, pure LLM answer.

Example using Perplexity:

```bash
python main.py \
  --config config.yaml \
  ask \
  --provider perplexity \
  --model sonar-pro \
  "What is 2 + 2?"
```

Typical output:

```text
2 + 2 equals 4.
```

Another example (OpenAI) if enabled and configured:

```bash
python main.py \
  --config config.yaml \
  ask \
  --provider openai \
  --model gpt4o-mini \
  "Explain Linux in simple terms."
```

---

### Agent mode (single task with tools)

Agent mode lets the model use tools to accomplish a task.

The agent:

1. Calls the model with the system prompt and your task.
2. Expects either:

   * a JSON tool call, or
   * a final answer.
3. When JSON tool call is present:

   * Runs the requested tool,
   * Feeds tool results back into the conversation.
4. Repeats until:

   * a final answer is produced, or
   * `max_steps` is reached.

Example: inspect RAM usage with `free -h` and explain it:

```bash
python main.py \
  --config config.yaml \
  agent \
  --provider perplexity \
  --model sonar-small \
  --max-steps 4 \
  "Use the shell_command tool to run 'free -h' on my Linux system and then explain my RAM usage in simple terms."
```

If everything is configured correctly and `shell` is enabled, the agent will execute `free -h` on your machine and then summarize the results.

> Note: Perplexity models are not officially “tool-calling models” like some OpenAI/Anthropic models, so prompt design matters a lot if you want consistent JSON tool calls.

---

### Chat mode (interactive session)

Chat mode keeps an interactive REPL-style session open in your terminal until you exit.

You choose between:

* `--mode ask` → normal chat, no tools.
* `--mode agent` → chat where the agent is allowed to use tools in each turn.

You can exit using `/exit`, `/quit`, or Ctrl+C.

#### Chat in ask mode

```bash
python main.py \
  --config config.yaml \
  chat \
  --mode ask \
  --provider perplexity \
  --model sonar-pro
```

Example session:

```text
[Interactive chat started in ASK mode]
Provider: perplexity
Model   : sonar-pro
Type /exit or press Ctrl+C to end the session.

You> what is Linux?
Assistant> Linux is an open-source operating system kernel that...
You> explain it like I'm 10
Assistant> ...
You> /exit
Bye 👋
```

#### Chat in agent mode

```bash
python main.py \
  --config config.yaml \
  chat \
  --mode agent \
  --provider perplexity \
  --model sonar-small \
  --max-steps 4
```

Example session:

```text
[Interactive chat started in AGENT mode]
Provider: perplexity
Model   : sonar-small
Type /exit or press Ctrl+C to end the session.

You> Use the shell_command tool to run 'free -h' on my Linux system and then explain my RAM usage.
Assistant> ... (the agent will attempt to call the shell tool and then explain)
You> /exit
Bye 👋
```

---

## Tools & Permissions

Tools are controlled by the `tools:` section in `config.yaml`.

### ShellCommandTool (`shell_command`)

Configured under `tools.shell`:

* `enabled`: whether the tool is active.
* `working_dir`: default working directory for commands.
* `allowed_commands`:

  * If list is empty (`[]`), **no restriction** → the model can attempt any command.
  * To restrict:

    ```yaml
    allowed_commands:
      - free
      - lscpu
      - top
      - ls
      - cat
    ```

You should strongly consider restricting commands in non-test environments.

### ReadFileTool (`read_file`)

Configured under `tools.read_file`:

* `enabled`: enable/disable.
* `root_dir`: restricts the read access to this subtree only.

Example:

```yaml
read_file:
  enabled: true
  root_dir: ./workspace
```

The tool will refuse to read paths outside `./workspace`.

### WriteFileTool (`write_file`)

Configured under `tools.write_file`:

* `enabled`: enable/disable.
* `root_dir`: restricts where files can be created/modified.

Example:

```yaml
write_file:
  enabled: true
  root_dir: ./workspace
```

The tool will refuse to write outside `./workspace`.

### WebSearchTool / WebFetchTool

Configured under `tools.web_search` and `tools.web_fetch`:

* Typically:

  * Set `enabled: true` only if you have a proper external search API.
  * Provide:

    * `endpoint_env`: name of env var holding the API endpoint.
    * `api_key_env`: name of env var holding the API key.

If you are not using external web search, keep them disabled:

```yaml
web_search:
  enabled: false

web_fetch:
  enabled: false
```

---

## Security Notes

If you configure:

* `shell.enabled = true`
* `read_file.root_dir = /`
* `write_file.root_dir = /`
* `allowed_commands = []`

you essentially give the model a terminal and file access similar to your own user:

* It can read and modify any file you can.
* It can run any command you can.

Recommended safe practices:

* Use a **non-privileged user** (never run as root).
* Prefer using a dedicated **sandbox directory**:

  * `read_file.root_dir = ./workspace`
  * `write_file.root_dir = ./workspace`
* Restrict shell commands:

  * Only allow harmless diagnostics commands.
* Use a VM or containerized environment when experimenting.

---

## Extending the Project

### Adding a new provider / model

1. Create a new provider class in `agent/models/your_provider.py`.
2. Make it follow the same interface as other providers (e.g. `PerplexityProvider`):

   * `from_config(name: str, cfg: dict) -> ProviderInstance`
   * `chat(model: str, messages: list[dict], stream: bool = False) -> ChatResponse`
3. Register it in `build_model_registry` in `main.py`.
4. Add provider config under `providers:` in `config.yaml`.

Example config snippet:

```yaml
providers:
  myprovider:
    enabled: true
    api_key_env: MYPROVIDER_API_KEY
    base_url: https://api.myprovider.com
    models:
      my-model:
        name: my-model-id
        supports_tools: true
        supports_stream: true
        max_context_tokens: 4096
```

Then you can call:

```bash
python main.py \
  --config config.yaml \
  ask \
  --provider myprovider \
  --model my-model \
  "Hello!"
```

### Adding a new tool plugin

1. Create a new file in `agent/tools/my_tool.py`.
2. Implement a class exposing at least:

   * `name: str`
   * `description: str`
   * `@classmethod from_config(cls, config: dict) -> "MyTool"`
   * `run(self, tool_input: dict) -> str`
3. Register it in `build_tool_registry` (in `main.py`).
4. Add configuration under `tools:` in `config.yaml`.
5. Update `agent_system` prompt to describe how to call the new tool.

---

## Project Structure

A typical layout:

```text
ai-agent/
├─ agent/
│  ├─ core/
│  │  ├─ agent.py          # AskAgent and ToolAgent
│  │  ├─ router.py         # ModelRouter
│  │  └─ prompts.py        # PromptManager
│  ├─ models/
│  │  ├─ base.py           # Base provider, ChatResponse, ModelRegistry
│  │  ├─ openai_provider.py
│  │  ├─ perplexity_provider.py
│  │  └─ anthropic_provider.py
│  ├─ tools/
│  │  ├─ base.py           # ToolRegistry and base classes
│  │  ├─ shell.py          # ShellCommandTool
│  │  ├─ files.py          # ReadFileTool / WriteFileTool
│  │  └─ web.py            # WebSearchTool / WebFetchTool (optional)
│  └─ config.py            # load_app_config (YAML/TOML loader)
├─ main.py                 # CLI entrypoint (ask / agent / chat)
├─ config.yaml             # Providers, tools, prompts
├─ requirements.txt        # Python dependencies
├─ .env                    # API keys (not committed to Git)
└─ README.md               # Project documentation
```

---
