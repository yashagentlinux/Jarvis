"""
plugins/system_plugin.py — System Utilities Plugin for Jarvis
=============================================================
Handles system-level utility actions: date/time, clipboard,
volume control, screen brightness, and system info queries.

Plugin interface:
    name    = "system_utils"
    actions = [...]
    execute(action, params) -> str
"""

import shutil
import subprocess
from datetime import datetime
from typing import Dict

# ── Plugin metadata ───────────────────────────
name    = "system_utils"
actions = [
    "show_date",
    "show_time",
    "show_datetime",
    "show_uptime",
    "show_disk_usage",
    "show_memory_usage",
    "show_ip_address",
    "volume_up",
    "volume_down",
    "volume_mute",
    "take_screenshot",
    "lock_screen",
]


# ── Helpers ───────────────────────────────────
def _run(cmd: list, capture: bool = True) -> tuple[bool, str]:
    """Run a command; return (success, output/error)."""
    path = shutil.which(cmd[0])
    if not path:
        return False, f"'{cmd[0]}' not found on this system."
    try:
        result = subprocess.run(
            [path] + cmd[1:],
            capture_output=capture,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or f"Command failed (exit {result.returncode})"
    except subprocess.TimeoutExpired:
        return False, f"'{cmd[0]}' timed out."
    except OSError as exc:
        return False, str(exc)


# ── Execute ───────────────────────────────────
def execute(action: str, params: Dict) -> str:
    """
    Dispatch a system utility action.

    Args:
        action (str): One of the strings in ``actions``.
        params (dict): Optional parameters (unused for most actions).

    Returns:
        str: Human-readable result message.
    """

    # ── Date / Time ──────────────────────────
    if action == "show_date":
        return f"Today is {datetime.now().strftime('%A, %d %B %Y')}. 📅"

    elif action == "show_time":
        return f"The current time is {datetime.now().strftime('%I:%M %p')}. 🕒"

    elif action == "show_datetime":
        return f"It is {datetime.now().strftime('%A, %d %B %Y  —  %I:%M %p')}. 📅🕒"

    # ── System Info ──────────────────────────
    elif action == "show_uptime":
        ok, out = _run(["uptime", "-p"])
        return f"System uptime: {out} ⏱" if ok else out

    elif action == "show_disk_usage":
        ok, out = _run(["df", "-h", "--output=source,size,used,avail,pcent", "/"])
        if ok:
            lines = out.splitlines()
            if len(lines) >= 2:
                header = lines[0]
                data   = lines[1]
                return f"Disk usage (root):\n  {header}\n  {data} 💾"
        return out

    elif action == "show_memory_usage":
        ok, out = _run(["free", "-h"])
        if ok:
            lines = [l for l in out.splitlines() if l]
            return f"Memory usage:\n  {chr(10).join(lines)} 🧠"
        return out

    elif action == "show_ip_address":
        ok, out = _run(["hostname", "-I"])
        if ok:
            ips = out.split()
            return f"IP address(es): {', '.join(ips)} 🌐"
        return out

    # ── Volume Controls ───────────────────────
    elif action == "volume_up":
        ok, out = _run(["amixer", "-D", "pulse", "sset", "Master", "10%+"], capture=True)
        return "🔊 Volume increased by 10%." if ok else f"Volume control unavailable: {out}"

    elif action == "volume_down":
        ok, out = _run(["amixer", "-D", "pulse", "sset", "Master", "10%-"], capture=True)
        return "🔉 Volume decreased by 10%." if ok else f"Volume control unavailable: {out}"

    elif action == "volume_mute":
        ok, out = _run(["amixer", "-D", "pulse", "sset", "Master", "toggle"], capture=True)
        return "🔇 Volume toggled (mute/unmute)." if ok else f"Volume control unavailable: {out}"

    # ── Screen / UI ───────────────────────────
    elif action == "take_screenshot":
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"/tmp/jarvis_screenshot_{ts}.png"
        # Try gnome-screenshot, scrot, then import (ImageMagick)
        for cmd in (
            ["gnome-screenshot", "-f", path],
            ["scrot", path],
            ["import", "-window", "root", path],
        ):
            ok, out = _run(cmd, capture=True)
            if ok:
                return f"📸 Screenshot saved to: {path}"
        return "Could not take a screenshot — install gnome-screenshot or scrot."

    elif action == "lock_screen":
        for cmd in (
            ["gnome-screensaver-command", "--lock"],
            ["loginctl", "lock-session"],
            ["xdg-screensaver", "lock"],
            ["dm-tool", "lock"],
        ):
            ok, _ = _run(cmd, capture=True)
            if ok:
                return "🔒 Screen locked."
        return "Could not lock screen — no compatible screen-locker found."

    return f"system_utils plugin: unknown action '{action}'."
