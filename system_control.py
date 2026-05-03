"""
system_control.py — OS-Level Command Executor for Jarvis
==========================================================
Provides two layers of dispatch:

  1. execute_action(action_name) — NEW primary entry point called by the
     AI intent router. Accepts a canonical action name string and runs
     the matching handler function.

  2. is_system_command() / execute_command() — legacy keyword-based shim
     retained for CLI (main.py) compatibility. They now delegate to the
     same handler functions used by execute_action().

All subprocesses use shell=False and start_new_session=True.
"""

import subprocess
import shutil
from datetime import datetime
from typing import Callable, Optional

from utils import logger, confirm_action, Colours

# Lazy import to avoid circular dependency
def _get_run_plugin():
    try:
        from plugin_loader import run_plugin_action
        return run_plugin_action
    except ImportError:
        return None


# ─────────────────────────────────────────────
# Action Registry
# ─────────────────────────────────────────────
# Maps canonical action name → handler function.
# Populated via the @register decorator below.
_ACTION_REGISTRY: dict[str, Callable[[], str]] = {}


def register(name: str):
    """Decorator: register a handler function under ``name``."""
    def decorator(fn: Callable[[], str]) -> Callable[[], str]:
        _ACTION_REGISTRY[name] = fn
        return fn
    return decorator


# ─────────────────────────────────────────────
# Primary Public Interface (Intent Router)
# ─────────────────────────────────────────────
def execute_action(action_name: str) -> str:
    """
    Execute a system action by its canonical name.

    Called by the AI intent router in gui.py / JarvisWorker after
    detect_intent() returns a "system" classification.

    Args:
        action_name (str): One of the keys in _ACTION_REGISTRY, e.g.
                           "launch_firefox", "show_time", "shutdown_system".

    Returns:
        str: Human-readable result message.
    """
    # ── Try Plugin Registry first ──────────
    run_plugin = _get_run_plugin()
    if run_plugin:
        plugin_result = run_plugin(action_name)
        if plugin_result is not None:
            return plugin_result

    # ── Fallback to Built-in Handlers ──────
    handler = _ACTION_REGISTRY.get(action_name)
    if handler:
        logger.info(f"execute_action: running built-in '{action_name}'")
        return handler()

    logger.warning(f"execute_action: unknown action '{action_name}'")
    return f"I don't know how to perform the action '{action_name}'."


def get_registered_actions() -> list[str]:
    """Return a sorted list of all registered action names (for debugging)."""
    return sorted(_ACTION_REGISTRY.keys())


# ─────────────────────────────────────────────
# Legacy Keyword-Based Shim (CLI / offline use)
# ─────────────────────────────────────────────
# Maps keyword fragments → action name. Used only by is_system_command()
# and execute_command() for the terminal CLI (main.py).
_KEYWORD_MAP: list[tuple[tuple[str, ...], str]] = [
    (("open firefox",),                                        "launch_firefox"),
    (("open chrome", "open google chrome"),                    "launch_chrome"),
    (("open terminal", "open console"),                        "launch_terminal"),
    (("open files", "open file manager", "open nemo",
      "open nautilus"),                                        "launch_file_manager"),
    (("show date and time", "date and time",
      "current date and time"),                                "show_datetime"),
    (("show date", "what date", "today's date",
      "current date"),                                         "show_date"),
    (("show time", "what time", "current time",
      "what's the time"),                                      "show_time"),
    (("shutdown system", "shut down", "power off"),            "shutdown_system"),
    (("restart system", "reboot system", "reboot"),            "restart_system"),
]


def is_system_command(user_input: str) -> bool:
    """
    Keyword-based check used by the CLI (main.py).
    The GUI uses detect_intent() from ai_engine instead.
    """
    lower = user_input.lower().strip()
    return any(
        any(kw in lower for kw in keywords)
        for keywords, _ in _KEYWORD_MAP
    )


def execute_command(user_input: str) -> str:
    """
    Keyword-based dispatcher for the CLI (main.py).
    Routes to execute_action() once a match is found.
    """
    lower = user_input.lower().strip()
    for keywords, action_name in _KEYWORD_MAP:
        if any(kw in lower for kw in keywords):
            return execute_action(action_name)

    logger.warning(f"execute_command: no keyword match for '{user_input}'")
    return "I couldn't match that to a known system command."


# ─────────────────────────────────────────────
# Helper: Launch an Application
# ─────────────────────────────────────────────
def _launch_app(candidates: list[str], friendly_name: str) -> str:
    """
    Try each binary name in ``candidates`` until one is found, then launch it.

    Args:
        candidates: Ordered list of binary names to try (e.g. ["firefox"]).
        friendly_name: Display name shown in the response message.

    Returns:
        str: Status message for the user.
    """
    for binary in candidates:
        path = shutil.which(binary)
        if path:
            try:
                subprocess.Popen(
                    [path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                logger.info(f"Launched {friendly_name} via '{path}'")
                return f"Opening {friendly_name}... 🚀"
            except OSError as exc:
                logger.error(f"_launch_app: failed to launch '{binary}': {exc}")
                return f"Found {friendly_name} but couldn't launch it: {exc}"

    logger.warning(f"_launch_app: {friendly_name} not found. Tried: {candidates}")
    return (
        f"I couldn't find {friendly_name} on your system.\n"
        f"Tried: {', '.join(candidates)}\n"
        f"Install it first, then try again."
    )


# ─────────────────────────────────────────────
# Registered Action Handlers
# ─────────────────────────────────────────────

# ── Browsers ──────────────────────────────────
@register("launch_firefox")
def launch_firefox() -> str:
    """Launch Firefox web browser."""
    return _launch_app(["firefox", "firefox-esr"], "Firefox")


@register("launch_chrome")
def launch_chrome() -> str:
    """Launch Google Chrome or Chromium."""
    return _launch_app(
        ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
        "Google Chrome",
    )


# ── System Apps ───────────────────────────────
@register("launch_terminal")
def launch_terminal() -> str:
    """Launch the preferred terminal emulator."""
    return _launch_app(
        ["x-terminal-emulator", "gnome-terminal", "xterm", "xfce4-terminal",
         "mate-terminal", "tilix", "alacritty", "kitty"],
        "Terminal",
    )


@register("launch_file_manager")
def launch_file_manager() -> str:
    """Launch the preferred graphical file manager."""
    return _launch_app(
        ["nemo", "nautilus", "thunar", "dolphin", "pcmanfm", "caja"],
        "File Manager",
    )


# ── Date / Time ───────────────────────────────
@register("show_date")
def show_date() -> str:
    """Return today's date as a friendly string."""
    return f"Today is {datetime.now().strftime('%A, %d %B %Y')}. 📅"


@register("show_time")
def show_time() -> str:
    """Return the current time as a friendly string."""
    return f"The current time is {datetime.now().strftime('%I:%M %p')}. 🕒"


@register("show_datetime")
def show_datetime() -> str:
    """Return both current date and time."""
    return f"It is {datetime.now().strftime('%A, %d %B %Y  —  %I:%M %p')}. 📅🕒"


# ── Power Management ──────────────────────────
# NOTE: These handlers call confirm_action() which blocks on stdin.
# In GUI mode the caller (JarvisWorker) must obtain confirmation via
# a Qt dialog BEFORE calling execute_action(), then pass a pre-confirmed
# variant. See gui.py _DESTRUCTIVE_ACTIONS and _confirm_destructive().

@register("shutdown_system")
def shutdown_system() -> str:
    """Shut down the system (confirmation must be obtained by the caller)."""
    logger.info("Executing system SHUTDOWN.")
    for cmd in (["systemctl", "poweroff"], ["shutdown", "-h", "now"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, check=True)
                return "Shutting down... Goodbye! 👋"
            except subprocess.CalledProcessError as exc:
                logger.error(f"shutdown_system: {cmd} failed — {exc}")
    return "Could not shut down automatically.\nPlease run: sudo shutdown -h now"


@register("restart_system")
def restart_system() -> str:
    """Restart the system (confirmation must be obtained by the caller)."""
    logger.info("Executing system RESTART.")
    for cmd in (["systemctl", "reboot"], ["shutdown", "-r", "now"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, check=True)
                return "Restarting... See you on the other side! 🔄"
            except subprocess.CalledProcessError as exc:
                logger.error(f"restart_system: {cmd} failed — {exc}")
    return "Could not restart automatically.\nPlease run: sudo shutdown -r now"
