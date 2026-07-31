"""Tests for history persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research_agent.memory.history import add_paper, get_last_email_sent_time, is_duplicate, load_history, mark_email_sent
from research_agent.models.paper import Paper


class HistoryMemoryTests(unittest.TestCase):
    def test_load_history_returns_empty_history_when_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.json"

            history = load_history(history_path)

            self.assertEqual(history, {"schema_version": 1, "last_email_sent_time": None, "records": []})

    def test_is_duplicate_matches_exact_arxiv_id(self) -> None:
        history = {
            "schema_version": 1,
            "records": [
                {
                    "arxiv_id": "2401.12345",
                    "title": "Existing Paper",
                }
            ],
        }
        paper = self._paper(arxiv_id="2401.12345")

        self.assertTrue(is_duplicate(paper, history))
        self.assertFalse(is_duplicate(self._paper(arxiv_id="2401.99999"), history))

    def test_add_paper_writes_new_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.json"
            paper = self._paper()

            added = add_paper(paper, history_path=history_path, pushed_time="2024-01-03T00:00:00+00:00")

            self.assertTrue(added)
            saved = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema_version"], 1)
            self.assertEqual(len(saved["records"]), 1)
            self.assertEqual(saved["records"][0]["arxiv_id"], "2401.12345")
            self.assertEqual(saved["records"][0]["pushed_time"], "2024-01-03T00:00:00+00:00")
            self.assertIn("first_seen_time", saved["records"][0])

    def test_add_paper_does_not_write_duplicate_arxiv_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.json"
            paper = self._paper()

            self.assertTrue(add_paper(paper, history_path=history_path))
            self.assertFalse(add_paper(paper, history_path=history_path))

            saved = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["records"]), 1)

    def test_mark_email_sent_updates_last_email_sent_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.json"

            mark_email_sent(history_path=history_path, sent_time="2024-01-05T00:00:00+00:00")
            history = load_history(history_path)

            self.assertEqual(get_last_email_sent_time(history), "2024-01-05T00:00:00+00:00")

    def test_get_last_email_sent_time_falls_back_to_latest_pushed_time(self) -> None:
        history = {
            "schema_version": 1,
            "records": [
                {"arxiv_id": "1", "pushed_time": "2024-01-01T00:00:00+00:00"},
                {"arxiv_id": "2", "pushed_time": "2024-01-03T00:00:00+00:00"},
            ],
        }

        self.assertEqual(get_last_email_sent_time(history), "2024-01-03T00:00:00+00:00")

    @staticmethod
    def _paper(arxiv_id: str = "2401.12345") -> Paper:
        return Paper(
            arxiv_id=arxiv_id,
            title="Soccer Video Understanding with Multimodal Agents",
            authors=["Ada Lovelace", "Alan Turing"],
            abstract="A paper about soccer video understanding.",
            published="2024-01-02T03:04:05+00:00",
            pdf_url="https://arxiv.org/pdf/2401.12345v2",
        )


if __name__ == "__main__":
    unittest.main()
