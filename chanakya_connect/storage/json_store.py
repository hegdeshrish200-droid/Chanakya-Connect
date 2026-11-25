"""
JSON Persistence Layer for ChanakyaConnect.

Storage ONLY keeps raw data (users, edges, pending requests, posts, notifications).
All graph computations (BFS degree/path, Jaccard suggestions, Trie prefix search,
MaxHeap feed merging, Stack undo/nav, Queue notifications) run strictly in memory
on Python data structures inside `core/engine.py`.
"""

import json
import os
from typing import Any, Dict


class JsonStorage:
    """Atomic JSON file persistence for the networking app."""

    def __init__(self, filepath: str = "data/network_data.json") -> None:
        self.filepath = filepath
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.filepath):
            return {
                "users": [],
                "connections": [],
                "pending_requests": [],
                "posts": [],
                "notifications": {},
            }
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, state: Dict[str, Any]) -> None:
        """Write atomically via temp file + os.replace to prevent corruption."""
        tmp_path = f"{self.filepath}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, self.filepath)
