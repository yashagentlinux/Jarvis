"""
long_memory.py — Persistent Long-Term Memory for Jarvis
========================================================
Stores every conversation turn to a JSON file on disk so that
meaningful interactions survive across sessions.

Public API:
    save_interaction(user_msg, assistant_msg, tags=[])
    load_recent(n=20)  → list of dicts
    search_memory(query, top_n=5)  → list of matching dicts
    get_stats()  → dict with total counts / date range
"""

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from utils import logger

# ─────────────────────────────────────────────
# Storage location
# ─────────────────────────────────────────────
_MEMORY_FILE = Path(__file__).parent / "long_memory.json"
_LOCK = threading.Lock()          # file-level write lock


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────
def _load_raw() -> List[Dict]:
    """Read the JSON memory file; return an empty list if absent/corrupt."""
    if not _MEMORY_FILE.exists():
        return []
    try:
        with _MEMORY_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"long_memory: could not read file — {exc}")
        return []


def _write_raw(records: List[Dict]) -> None:
    """Atomically overwrite the memory file (write-then-rename)."""
    tmp = _MEMORY_FILE.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)
        tmp.replace(_MEMORY_FILE)
    except OSError as exc:
        logger.error(f"long_memory: write failed — {exc}")


def _score(record: Dict, query_tokens: List[str]) -> int:
    """
    Simple term-frequency relevance score for search_memory().
    Counts how many unique query tokens appear in the record's text.
    """
    haystack = (
        record.get("user", "").lower()
        + " "
        + record.get("assistant", "").lower()
        + " "
        + " ".join(record.get("tags", []))
    )
    return sum(1 for tok in query_tokens if tok in haystack)


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
def save_interaction(
    user_msg: str,
    assistant_msg: str,
    tags: Optional[List[str]] = None,
) -> None:
    """
    Append a single user/assistant exchange to long-term memory.

    Args:
        user_msg (str):       The user's original input.
        assistant_msg (str):  Jarvis's response.
        tags (list[str]):     Optional topic labels for easier retrieval.
    """
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user": user_msg.strip(),
        "assistant": assistant_msg.strip(),
        "tags": [t.lower() for t in (tags or [])],
    }
    with _LOCK:
        records = _load_raw()
        records.append(record)
        _write_raw(records)
    logger.debug(f"long_memory: saved interaction (total={len(records)}).")


def load_recent(n: int = 20) -> List[Dict]:
    """
    Return the last *n* interactions, newest first.

    Args:
        n (int): How many records to return.

    Returns:
        list[dict]: Records with keys: timestamp, user, assistant, tags.
    """
    records = _load_raw()
    return list(reversed(records[-n:]))


def search_memory(query: str, top_n: int = 5) -> List[Dict]:
    """
    Full-text search across all stored interactions.

    Tokenises ``query`` by word, scores each record by how many unique
    query words appear in its text, and returns the top matches.

    Args:
        query (str): Free-text search string.
        top_n (int): Maximum number of results to return.

    Returns:
        list[dict]: Best-matching records, highest score first.
    """
    query_tokens = re.findall(r"\w+", query.lower())
    if not query_tokens:
        return []

    records = _load_raw()
    scored = [
        (rec, _score(rec, query_tokens))
        for rec in records
        if _score(rec, query_tokens) > 0
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [rec for rec, _ in scored[:top_n]]


def get_stats() -> Dict:
    """
    Return summary statistics about the stored memory.

    Returns:
        dict: {total, oldest, newest}
    """
    records = _load_raw()
    if not records:
        return {"total": 0, "oldest": None, "newest": None}
    return {
        "total": len(records),
        "oldest": records[0].get("timestamp"),
        "newest": records[-1].get("timestamp"),
    }


def clear_memory() -> int:
    """
    Delete all stored long-term memory records.

    Returns:
        int: Number of records that were deleted.
    """
    with _LOCK:
        records = _load_raw()
        count = len(records)
        _write_raw([])
    logger.info(f"long_memory: cleared {count} records.")
    return count
