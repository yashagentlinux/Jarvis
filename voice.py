"""
voice.py — High-Reliability Voice I/O for Linux
==============================================
Uses the 'espeak' system command directly to bypass library bugs.
"""

import os
import subprocess
import speech_recognition as sr
from utils import logger

class VoiceManager:
    def __init__(self):
        self.MIC_INDEX = 0
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True

    def speak(self, text: str):
        """Speak using the system 'espeak' command (most reliable on Linux)."""
        clean_text = text.replace('"', '').replace("'", "").replace("*", "")
        print(f"Jarvis: {clean_text}")
        
        try:
            # -s 160: speed, -a 100: amplitude, -v en-us: American English
            subprocess.run(["espeak", "-s", "160", "-a", "100", "-v", "en-us", clean_text], 
                           stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Voice Error: {e}")

    def listen(self) -> str:
        """Listen via mic with fallback logic."""
        try:
            with sr.Microphone(device_index=self.MIC_INDEX) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info("Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
                text = self.recognizer.recognize_google(audio)
                return text
        except Exception as e:
            logger.error(f"Mic error: {e}")
            if self.MIC_INDEX == 0: 
                self.MIC_INDEX = 1
            return ""
