"""Backward-compatible imports for repository-backed paper history."""

from research_agent.memory.history import add_paper, is_duplicate, load_history

__all__ = ["load_history", "is_duplicate", "add_paper"]
