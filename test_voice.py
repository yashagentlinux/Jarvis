import pyttsx3
import os

def test_voice():
    print("Initializing TTS engine...")
    try:
        engine = pyttsx3.init()
        print("Engine initialized successfully.")
        
        voices = engine.getProperty('voices')
        print(f"Total voices found: {len(voices)}")
        
        # Test with default voice
        print("Attempting to speak 'Hello, I am testing my voice.'")
        engine.say("Hello, I am testing my voice.")
        engine.runAndWait()
        print("Speech command finished.")
        
    except Exception as e:
        print(f"FAILED: {e}")
        print("\nTIP: On Linux, ensure 'espeak' and 'libespeak-dev' are installed.")
        print("Run: sudo apt install espeak libespeak-dev")

if __name__ == "__main__":
    test_voice()
