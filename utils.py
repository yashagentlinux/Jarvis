"""
utils.py — Unified Utility Helpers for Jarvis
==============================================
Provides logging, console formatting, and audio debugging.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
# Paths & Settings
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "jarvis.log"
DEBUG_MODE: bool = os.environ.get("JARVIS_DEBUG", "0").strip() == "1"

# ─────────────────────────────────────────────
# ANSI Colour Codes
# ─────────────────────────────────────────────
class Colours:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE    = "\033[94m"

# ─────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────
def setup_logger(name: str = "jarvis") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(module)s | %(message)s")
    file_handler.setFormatter(file_fmt)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.WARNING)
    console_fmt = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_fmt)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger()

# ─────────────────────────────────────────────
# UI Helpers
# ─────────────────────────────────────────────
def get_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12: return "Good morning"
    elif hour < 17: return "Good afternoon"
    else: return "Good evening"

# ─────────────────────────────────────────────
# Audio Debug Utility
# ─────────────────────────────────────────────
def list_microphones():
    """Debug utility to list all available audio input devices."""
    try:
        import speech_recognition as sr
        print(f"\n{Colours.YELLOW}--- Available Microphones ---{Colours.RESET}")
        mics = sr.Microphone.list_microphone_names()
        if not mics:
            print("No microphones detected.")
        for i, name in enumerate(mics):
            print(f"Index {i}: {name}")
        print(f"{Colours.YELLOW}----------------------------{Colours.RESET}\n")
    except Exception as e:
        print(f"Error listing microphones: {e}")

if __name__ == "__main__":
    list_microphones()
