"""
ai_engine.py — Refined REST API Integration for Jarvis
======================================================
Uses v1beta endpoint and precise model pathing.
"""

import os
import json
import http.client
from utils import logger

class JarvisAI:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.host = "generativelanguage.googleapis.com"
        # Try the most likely successful model ID
        self.model_id = "gemini-1.5-flash"

    def ask(self, prompt: str) -> str:
        """Send query via direct REST API with fallback to v1beta/v1 endpoints."""
        if not self.api_key:
            return "I'm offline. No API key found."

        # Switching to v1beta as it has better support for Flash models
        url = f"/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        
        headers = {'Content-Type': 'application/json'}
        body = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        try:
            conn = http.client.HTTPSConnection(self.host)
            conn.request("POST", url, body=json.dumps(body), headers=headers)
            response = conn.getresponse()
            data = response.read().decode('utf-8')
            conn.close()

            result = json.loads(data)

            if response.status == 200:
                try:
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
                except (KeyError, IndexError):
                    return "I received a response, but couldn't parse the text."
            else:
                error_msg = result.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Gemini REST Error ({response.status}): {error_msg}")
                
                # If v1beta/1.5-flash fails, try a different stable combination
                if response.status == 404 and self.model_id != "gemini-pro":
                    logger.warning("Retrying with gemini-pro...")
                    self.model_id = "gemini-pro"
                    return self.ask(prompt)
                    
                return f"API Error: {error_msg}"

        except Exception as e:
            logger.error(f"Network error in AI Engine: {e}")
            return "I'm having trouble connecting to the internet."
