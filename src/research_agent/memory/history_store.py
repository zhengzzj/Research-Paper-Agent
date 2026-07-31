"""Backward-compatible imports for repository-backed paper history."""

from research_agent.memory.history import add_paper, get_last_email_sent_time, is_duplicate, load_history, mark_email_sent

__all__ = ["load_history", "is_duplicate", "add_paper", "get_last_email_sent_time", "mark_email_sent"]
