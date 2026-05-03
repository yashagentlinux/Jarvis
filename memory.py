"""
memory.py — Conversation Memory Manager for Jarvis
====================================================
Maintains a rolling window of the last N user-assistant exchanges.
This short-term memory is passed to Gemini for contextual responses.
"""

from collections import deque
from typing import List, Dict


class ConversationMemory:
    """
    Manages short-term conversational memory for Jarvis.

    Stores the last `max_turns` user/assistant exchanges so that
    Gemini can understand context across a session.
    """

    def __init__(self, max_turns: int = 5):
        """
        Initialize the memory buffer.

        Args:
            max_turns (int): Maximum number of exchanges to retain.
        """
        self.max_turns = max_turns
        # Each entry: {"role": "user"|"assistant", "content": "..."}
        self._history: deque = deque(maxlen=max_turns * 2)  # *2 for user+assistant pairs

    def add_user_message(self, message: str) -> None:
        """
        Record a user message into memory.

        Args:
            message (str): The user's raw input text.
        """
        self._history.append({"role": "user", "content": message.strip()})

    def add_assistant_message(self, message: str) -> None:
        """
        Record an assistant response into memory.

        Args:
            message (str): The assistant's response text.
        """
        self._history.append({"role": "assistant", "content": message.strip()})

    def get_history(self) -> List[Dict[str, str]]:
        """
        Return the full conversation history as a list of dicts.

        Returns:
            List[Dict[str, str]]: Ordered list of {"role", "content"} dicts.
        """
        return list(self._history)

    def format_for_prompt(self) -> str:
        """
        Format conversation history as a readable string for Gemini's system prompt.

        Returns:
            str: Multi-line string of previous exchanges.
        """
        if not self._history:
            return ""

        lines = ["[Previous conversation context:]"]
        for entry in self._history:
            role_label = "You" if entry["role"] == "user" else "Jarvis"
            lines.append(f"  {role_label}: {entry['content']}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Wipe all stored conversation history."""
        self._history.clear()

    def __len__(self) -> int:
        return len(self._history)

    def __repr__(self) -> str:
        return f"ConversationMemory(turns={len(self._history)}, max={self.max_turns * 2})"
