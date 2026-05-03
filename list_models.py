import os
import google.generativeai as genai

def list_my_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        return
    
    genai.configure(api_key=api_key)
    print("\n--- Available Models ---")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Name: {m.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_my_models()
