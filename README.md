# J.A.R.V.I.S — Just A Rather Very Intelligent System
### v3.0 — Autonomous Agent Edition

> A production-quality, modular AI desktop assistant for Linux Mint.
> Powered by Google Gemini 1.5 Flash with plugin support, long-term memory, and autonomous task execution.

---

## What's New in v3.0

| Feature | Description |
|---|---|
| **Autonomous Mode** | Click 🤖 Auto — Jarvis plans and executes multi-step tasks via Gemini |
| **Plugin System** | Drop `.py` files into `plugins/` — auto-discovered at startup |
| **Long-Term Memory** | Every conversation saved to `long_memory.json`, searchable across sessions |
| **Task Chain Engine** | Sequential multi-action execution with deduplication and safe-mode gate |
| **Background Agent Loop** | Daemon thread processes queued tasks without blocking the UI |
| **AI Action Planning** | `plan_actions()` generates structured step-by-step plans from natural language |
| **Debug Mode** | `JARVIS_DEBUG=1` enables verbose console logging |

---

## Project Structure

```
JARVIS/
├── main.py              # CLI entry point
├── gui.py               # PyQt5 desktop GUI (primary interface)
│
├── ai_engine.py         # Gemini: ask() + detect_intent() + plan_actions()
├── system_control.py    # OS action registry (@register decorator)
├── memory.py            # Short-term rolling memory (5-turn window)
├── long_memory.py       # Persistent JSON memory — save/load/search
├── task_engine.py       # Multi-step task chain executor
├── plugin_loader.py     # Auto-discovers & loads plugins/ directory
├── agent_loop.py        # Background daemon — autonomous task queue
│
├── plugins/
│   ├── browser_plugin.py   # Firefox, Chrome, Google search, YouTube
│   └── system_plugin.py    # Date/time, disk, memory, volume, screenshot
│
├── requirements.txt     # pip dependencies
├── .env.example         # API key template
├── jarvis.log           # Auto-created — all session logs
├── long_memory.json     # Auto-created — persistent conversation history
└── README.md            # This file
```

---

## Quick Start

### 1 — Install prerequisites (one-time)

```bash
sudo apt install python3-venv python3-pip portaudio19-dev python3-pyaudio espeak
```

### 2 — Set up virtualenv

```bash
cd /home/yash/Desktop/JARVIS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3 — Set your API key

```bash
export GEMINI_API_KEY="your_key_here"
# Get a free key at: https://aistudio.google.com/app/apikey
```

### 4 — Run

```bash
# Desktop GUI (recommended)
python gui.py

# Terminal CLI
python main.py

# With verbose debug logging
JARVIS_DEBUG=1 python gui.py
```

---

## Commands & Features

### Built-in System Commands

| What you say | Action |
|---|---|
| `open firefox` / `launch firefox` | Launch Firefox |
| `open chrome` | Launch Chrome / Chromium |
| `open terminal` | Open terminal emulator |
| `open files` | Open file manager |
| `show date` / `show time` | Date and/or time |
| `search youtube for lo-fi` | Open YouTube search |
| `search google for python tips` | Open Google search |
| `show disk usage` | Disk info via plugin |
| `show memory usage` | RAM info via plugin |
| `show ip address` | Local IP address |
| `take screenshot` | Save PNG to /tmp |
| `lock screen` | Lock the desktop |
| `volume up` / `volume down` | Adjust volume 10% |
| `shutdown system` | With confirmation dialog |
| `restart system` | With confirmation dialog |
| *Anything else* | Forwarded to Gemini AI |

### Autonomous Mode (🤖 Auto button)

Click the **🤖 Auto** button in the header to enable AI planning mode.

**Example:**
> You: "I want to watch music videos"

Jarvis will automatically:
1. Open Firefox
2. Search YouTube for "music videos"

---

## Plugin System

### Writing a Custom Plugin

Create `plugins/my_plugin.py`:

```python
name    = "my_plugin"
actions = ["do_something", "do_other_thing"]

def execute(action: str, params: dict) -> str:
    if action == "do_something":
        return "Did something! ✅"
    elif action == "do_other_thing":
        query = params.get("query", "")
        return f"Did other thing with: {query}"
    return f"Unknown action: {action}"
```

Restart Jarvis — it's automatically loaded. No other changes needed.

### Hot-Reload Plugins (in Python)

```python
import plugin_loader
plugin_loader.reload_plugins()
```

---

## Long-Term Memory

All conversations are automatically saved to `long_memory.json`.

```python
from long_memory import load_recent, search_memory, get_stats

# Last 10 conversations
recent = load_recent(n=10)

# Search for conversations about Python
results = search_memory("python programming")

# Stats
stats = get_stats()
print(f"Total: {stats['total']}, From: {stats['oldest']}")
```

---

## Agent Loop (Background Automation)

```python
from agent_loop import AgentLoop

agent = AgentLoop(interval=5.0)
agent.start()

# Queue actions for background execution
agent.enqueue("take_screenshot")
agent.enqueue_chain(["show_time", "launch_firefox"])

agent.stop()
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `JARVIS_DEBUG` | `0` | Set to `1` for verbose console logs |

---

## Architecture Overview

```
User Input (text / voice)
        │
        ▼
   JarvisWorker (QThread)
        │
        ├─ Autonomous Mode ON?
        │       ├─ YES → ai.plan_actions() → task_engine.execute_task_chain()
        │       └─ NO  → ai.detect_intent()
        │                    ├─ "system" → _run_action() → plugin_loader / system_control
        │                    └─ "ai"     → ai.ask() → Gemini response
        │
        ▼
   long_memory.save_interaction()   ← persists every exchange
        │
        ▼
   response_ready signal → JarvisWindow → ChatBubble + TTSWorker

Background:
   AgentLoop (daemon thread) ← on_result → QTimer.singleShot → ChatBubble
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `GEMINI_API_KEY not set` | `export GEMINI_API_KEY="..."` |
| `ModuleNotFoundError` | `pip install -r requirements.txt` in venv |
| Plugin not loading | Check plugin has `name`, `actions`, `execute()` attributes |
| Mic not working | `sudo apt install portaudio19-dev python3-pyaudio` |
| Rate limit from Gemini | Wait 60s; free tier has per-minute limits |
| Autonomous mode not planning | Needs `GEMINI_API_KEY` set and internet connection |

---

## Future Roadmap

- **Wake-word detection** (`openwakeword`, always-listening daemon)
- **Scheduled tasks** (cron-style jobs via AgentLoop)
- **File operations plugin** (search, move, compress, read)
- **Email / calendar integration** (OAuth2)
- **Home Assistant / MQTT bridge** (IoT control)
- **Web dashboard** (Flask/FastAPI + React frontend)
