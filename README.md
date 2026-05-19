# Tiny OpenClaw

Tiny OpenClaw is a small personal AI assistant that runs on your machine and talks to you through Telegram.

It keeps per-chat conversation history, can save simple user memories, loads local "skills" as tools, and can switch between:

- Anthropic models through the Anthropic Messages API
- A local Gemma/Llama-style model served by LM Studio through its OpenAI-compatible API

## How It Works

The main flow is:

1. `main.py` loads environment variables and starts the app.
2. `telegram_channel.py` receives Telegram messages and sends replies.
3. `session_manager.py` stores conversation history in `SESSIONS.json`.
4. `context_builder.py` builds the system prompt from `SOUL.md`, available skills, memory, and current time.
5. `agent_runtime.py` runs the agent loop:
   - call the configured model provider
   - execute requested tools
   - send tool results back to the model
   - return the final answer
6. `model_providers.py` hides provider-specific API details for Anthropic and LM Studio.
7. `skill_loader.py` loads skills from the `skills/` directory.

## Current Skills

Skills live under `skills/<skill_name>/` and include a `SKILL.md` file plus a `handler.py`.

Included skills:

- `datetime`: get the current UTC date/time
- `memory_work`: save facts or notes to local memory
- `browser_use`: browse pages with Playwright

## Setup

Install `uv` first if you do not already have it:

```bash
brew install uv
```

Then run the macOS installer:

```bash
./scripts/install_macos.sh
```

On Windows, install `uv`:

```powershell
winget install --id=astral-sh.uv -e
```

Then run the Windows installer from PowerShell:

```powershell
.\scripts\install_windows.ps1
```

Create your local environment file:

```bash
cp .env.example .env
```

Then edit `.env`.

You can control log verbosity with:

```env
LOG_LEVEL=INFO
```

## Configuration

### Telegram

Create a Telegram bot with BotFather, then set:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### Anthropic

Use this configuration to run against Anthropic:

```env
MODEL_PROVIDER=anthropic
MODEL_NAME=your_anthropic_model
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### LM Studio

Start LM Studio's local server, load your model, then use:

```env
MODEL_PROVIDER=lmstudio
MODEL_NAME=local-model
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_API_KEY=not-needed
```

If LM Studio exposes a specific model id, use that value for `MODEL_NAME`.

## Run

Start the Telegram assistant:

```bash
uv run python main.py
```

You should see startup output in the terminal. Then send a message to your Telegram bot.

The app logs each Telegram turn, the configured model, loaded skills, tools offered to the model, tool calls requested by the model, and each tool execution result. This is the easiest way to confirm whether the local model is actually calling tools from the `skills/` directory.

To clear your Telegram chat session history, send one of these commands to the bot:

```text
/reset
/reset_session
/wipe_session
```

This clears the current chat's `SESSIONS.json` history. It does not clear saved long-term memory from `MEMORY.json`.

## Local State

The app writes local runtime state:

- `SESSIONS.json`: Telegram chat histories
- `MEMORY.json`: saved memory notes

These files are ignored by git because they may contain private user data.

## Development Notes

- Edit `SOUL.md` to change the assistant's personality and rules.
- Add a new skill by creating `skills/<name>/SKILL.md` and `skills/<name>/handler.py`.
- Use `MODEL_PROVIDER=anthropic` or `MODEL_PROVIDER=lmstudio` to switch model backends without changing agent runtime code.

## Quick Check

Run a syntax check:

```bash
uv run python -m py_compile main.py agent_runtime.py model_providers.py skill_loader.py
```
