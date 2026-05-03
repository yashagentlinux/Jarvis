import speech_recognition as sr
import pyttsx3

def diag():
    print("\n--- 🎙️ MICROPHONE LIST ---")
    mics = sr.Microphone.list_microphone_names()
    for i, name in enumerate(mics):
        print(f"Index {i}: {name}")
    
    print("\n--- 🔊 VOICE LIST (pyttsx3) ---")
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for i, voice in enumerate(voices):
        print(f"Index {i}: {voice.name} | Lang: {voice.languages} | ID: {voice.id}")

if __name__ == "__main__":
    diag()
