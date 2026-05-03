"""
main.py — CLI Entry Point for Jarvis
====================================
Implements the refined architecture:
User Input -> Command Router -> AI Fallback
"""

import os
import sys
import os
import sys

# --- Manual .env loader (removes python-dotenv dependency) ---
def load_env_manual(filepath=".env"):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value.strip().strip('"').strip("'")

load_env_manual()
# -----------------------------------------------------------

from ai_engine import JarvisAI
from commands import CommandHandler
from voice import VoiceManager
from utils import logger, get_greeting

class JarvisCLI:
    def __init__(self):
        self.ai = JarvisAI()
        self.cmd = CommandHandler()
        self.voice = VoiceManager()
        self.is_running = True

    def start(self):
        """Main CLI loop."""
        print(f"\n--- {get_greeting()}, I am JARVIS. ---")
        print("(Type 'exit' or 'quit' to stop, or just speak)\n")
        
        while self.is_running:
            try:
                # 1. Capture Input (Fixed "Double You" bug by using a single path)
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    self.voice.speak("Goodbye, Yash.")
                    self.is_running = False
                    break

                self._process_input(user_input)

            except KeyboardInterrupt:
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")

    def voice_mode(self):
        """Voice-only loop."""
        print("\n--- JARVIS Voice Mode Active ---")
        while self.is_running:
            try:
                text = self.voice.listen()
                if text:
                    print(f"Heard: {text}")
                    if "stop" in text.lower() or "exit" in text.lower():
                        self.voice.speak("Exiting voice mode.")
                        break
                    self._process_input(text)
            except KeyboardInterrupt:
                break

    def _process_input(self, text: str):
        """The core logic: Command First, then AI."""
        
        # 1. Try local commands first (Bypasses AI)
        command_response = self.cmd.handle(text)
        
        if command_response:
            self.voice.speak(command_response)
            return

        # 2. If no command match, use Gemini
        ai_response = self.ai.ask(text)
        self.voice.speak(ai_response)

if __name__ == "__main__":
    jarvis = JarvisCLI()
    
    # Check if user wants voice mode immediately via flag
    if "--voice" in sys.argv:
        jarvis.voice_mode()
    else:
        jarvis.start()
