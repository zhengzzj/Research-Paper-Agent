"""Paper metadata model definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Paper:
    """Unified paper metadata returned by paper sources."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    pdf_url: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return asdict(self)

