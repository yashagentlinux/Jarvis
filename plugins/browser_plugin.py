"""
plugins/browser_plugin.py — Browser Automation Plugin for Jarvis
=================================================================
Handles browser launching and (where possible) URL opening.

Plugin interface:
    name    = "browser"
    actions = [...]
    execute(action, params) -> str
"""

import shutil
import subprocess
from typing import Dict

# ── Plugin metadata ───────────────────────────
name    = "browser"
actions = [
    "launch_firefox",
    "launch_chrome",
    "open_url",
    "search_google",
    "search_youtube",
]


# ── Helpers ───────────────────────────────────
def _open_url_with_browser(url: str, friendly: str = "") -> str:
    """Try xdg-open, then firefox, then chrome to open a URL."""
    label = friendly or url
    for binary in ["xdg-open", "firefox", "google-chrome", "chromium"]:
        path = shutil.which(binary)
        if path:
            try:
                subprocess.Popen(
                    [path, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return f"Opening {label}... 🌐"
            except OSError:
                continue
    return f"Could not open {label} — no browser found."


def _launch_binary(candidates: list, friendly: str) -> str:
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
                return f"Opening {friendly}... 🚀"
            except OSError as exc:
                return f"Found {friendly} but couldn't launch it: {exc}"
    return f"Couldn't find {friendly}. Tried: {', '.join(candidates)}"


# ── Execute ───────────────────────────────────
def execute(action: str, params: Dict) -> str:
    """
    Dispatch a browser action.

    Args:
        action (str): One of the strings in ``actions``.
        params (dict): Optional parameters:
            url   (str) — for open_url
            query (str) — for search_google / search_youtube

    Returns:
        str: Human-readable result message.
    """
    if action == "launch_firefox":
        return _launch_binary(["firefox", "firefox-esr"], "Firefox")

    elif action == "launch_chrome":
        return _launch_binary(
            ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
            "Google Chrome",
        )

    elif action == "open_url":
        url = params.get("url", "https://www.google.com")
        return _open_url_with_browser(url)

    elif action == "search_google":
        query = params.get("query", "")
        if not query:
            return "Please provide a search query."
        import urllib.parse
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        return _open_url_with_browser(url, f"Google search for '{query}'")

    elif action == "search_youtube":
        query = params.get("query", "")
        if not query:
            url = "https://www.youtube.com"
            return _open_url_with_browser(url, "YouTube")
        import urllib.parse
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
        return _open_url_with_browser(url, f"YouTube search for '{query}'")

    return f"Browser plugin: unknown action '{action}'."
