"""
commands.py — Local Command Router for Jarvis
=============================================
This module handles all system-level actions locally.
Commands here are matched via keywords/regex BEFORE any AI processing.
"""

import os
import sys
import webbrowser
import subprocess
import shutil
from datetime import datetime
from utils import logger

class CommandHandler:
    def __init__(self):
        # Mapping keywords to internal methods
        self.commands = {
            "open youtube": self.open_youtube,
            "open google": self.open_google,
            "open terminal": self.open_terminal,
            "open file manager": self.open_files,
            "open files": self.open_files,
            "time": self.get_time,
            "date": self.get_date,
            "shutdown": self.shutdown,
            "restart": self.restart
        }

    def handle(self, text: str) -> str:
        """
        Check if the text contains a local command.
        Returns the result string if matched, else None.
        """
        text = text.lower().strip()
        
        # Check for direct keyword matches
        for cmd, func in self.commands.items():
            if cmd in text:
                logger.info(f"Local command matched: {cmd}")
                return func()
        
        return None

    # --- Command Implementations ---

    def open_youtube(self):
        webbrowser.open("https://www.youtube.com")
        return "Opening YouTube for you."

    def open_google(self):
        webbrowser.open("https://www.google.com")
        return "Opening Google."

    def open_terminal(self):
        # Linux Mint / Ubuntu common terminals
        terminals = ["gnome-terminal", "x-terminal-emulator", "xterm"]
        for t in terminals:
            if shutil.which(t):
                subprocess.Popen([t], start_new_session=True)
                return "Launching terminal."
        return "Could not find a terminal emulator."

    def open_files(self):
        # Nemo is default for Mint, Nautilus for Ubuntu
        managers = ["nemo", "nautilus", "xdg-open"]
        for m in managers:
            if shutil.which(m):
                if m == "xdg-open":
                    subprocess.Popen([m, os.path.expanduser("~")], start_new_session=True)
                else:
                    subprocess.Popen([m], start_new_session=True)
                return "Opening file manager."
        return "Could not open file manager."

    def get_time(self):
        now = datetime.now().strftime("%I:%M %p")
        return f"The current time is {now}."

    def get_date(self):
        today = datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {today}."

    def shutdown(self):
        # Safety: Just return the command info for CLI
        if sys.platform == "linux":
            # os.system("shutdown -h now") # Uncomment for real use
            return "Shutdown command detected. Please confirm in system dialog."
        return "Shutdown only supported on Linux."

    def restart(self):
        if sys.platform == "linux":
            # os.system("reboot") # Uncomment for real use
            return "Restart command detected."
        return "Restart only supported on Linux."
