"""Repository-backed paper history memory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_agent.models.paper import Paper


DEFAULT_HISTORY_PATH = Path("data/history.json")
SCHEMA_VERSION = 1


def load_history(history_path: str | Path = DEFAULT_HISTORY_PATH) -> dict[str, Any]:
    """Load the persistent paper history from JSON.

    If the history file does not exist yet, return an empty schema-compatible
    history object. This keeps local tests and first GitHub Actions runs simple.
    """
    path = Path(history_path)
    if not path.exists():
        return _empty_history()

    with path.open("r", encoding="utf-8") as file:
        history = json.load(file)

    if not isinstance(history, dict):
        raise ValueError(f"History file must contain a JSON object: {path}")

    history.setdefault("schema_version", SCHEMA_VERSION)
    history.setdefault("last_email_sent_time", None)
    history.setdefault("records", [])

    if not isinstance(history["records"], list):
        raise ValueError("History field 'records' must be a list.")

    return history


def is_duplicate(paper: Paper | dict[str, Any], history: dict[str, Any]) -> bool:
    """Return True when a paper's arXiv ID already exists in history."""
    arxiv_id = _paper_arxiv_id(paper)
    return any(record.get("arxiv_id") == arxiv_id for record in history.get("records", []))


def add_paper(
    paper: Paper | dict[str, Any],
    history_path: str | Path = DEFAULT_HISTORY_PATH,
    pushed_time: str | None = None,
) -> bool:
    """Add a paper to history if it is not already present.

    Returns True when a new record is written, or False when the paper is already
    present by exact arXiv ID match.
    """
    path = Path(history_path)
    history = load_history(path)

    if is_duplicate(paper, history):
        return False

    record = _paper_to_record(paper, pushed_time=pushed_time)
    history["records"].append(record)
    _write_history(history, path)
    return True


def get_last_email_sent_time(history: dict[str, Any]) -> str | None:
    """Return the latest successful email timestamp recorded in history."""
    explicit_value = history.get("last_email_sent_time")
    if isinstance(explicit_value, str) and explicit_value:
        return explicit_value

    pushed_times = [
        record.get("pushed_time")
        for record in history.get("records", [])
        if isinstance(record, dict) and isinstance(record.get("pushed_time"), str)
    ]
    return max(pushed_times) if pushed_times else None


def mark_email_sent(
    history_path: str | Path = DEFAULT_HISTORY_PATH,
    sent_time: str | None = None,
) -> None:
    """Persist the latest successful report email timestamp."""
    path = Path(history_path)
    history = load_history(path)
    history["last_email_sent_time"] = sent_time or _utc_now()
    _write_history(history, path)


def _paper_to_record(paper: Paper | dict[str, Any], pushed_time: str | None) -> dict[str, Any]:
    if isinstance(paper, Paper):
        record = paper.to_dict()
    else:
        record = dict(paper)

    now = _utc_now()
    record.setdefault("first_seen_time", now)
    record.setdefault("pushed_time", pushed_time or now)
    record.setdefault("quality_score", None)
    record.setdefault("relevance_score", None)
    return record


def _write_history(history: dict[str, Any], history_path: Path) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _paper_arxiv_id(paper: Paper | dict[str, Any]) -> str:
    if isinstance(paper, Paper):
        return paper.arxiv_id
    arxiv_id = paper.get("arxiv_id")
    if not isinstance(arxiv_id, str) or not arxiv_id:
        raise ValueError("Paper must include a non-empty 'arxiv_id'.")
    return arxiv_id


def _empty_history() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "last_email_sent_time": None, "records": []}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
