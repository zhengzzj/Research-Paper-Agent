"""Tests for the MVP pipeline."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from research_agent.main import PipelineDependencies, main, run_pipeline
from research_agent.models.paper import Paper


class MainPipelineTests(unittest.TestCase):
    def test_run_pipeline_fetches_deduplicates_analyzes_sends_and_updates_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self._write_config(temp_path, max_papers_per_run=1)
            history_path = temp_path / "history.json"
            history_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "records": [
                            {
                                "arxiv_id": "2401.00001",
                                "title": "Already Seen",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            sent_reports: list[tuple[str, list[Paper], dict[str, str]]] = []

            dependencies = PipelineDependencies(
                fetch_papers=lambda: [
                    self._paper("2401.00001", "Already Seen"),
                    self._paper("2401.00002", "Fresh Paper One"),
                    self._paper("2401.00003", "Fresh Paper Two"),
                ],
                analyze_paper=lambda paper: f"# Analysis for {paper.arxiv_id}",
                send_report_email=lambda subject, papers, analyses: sent_reports.append((subject, papers, analyses)),
            )

            result = run_pipeline(
                config_path=config_path,
                profile_path=temp_path / "research_profile.yaml",
                history_path=history_path,
                dependencies=dependencies,
            )

            self.assertEqual(result.fetched_count, 3)
            self.assertEqual(result.selected_count, 1)
            self.assertEqual(result.pushed_count, 1)
            self.assertEqual(len(sent_reports), 1)
            self.assertEqual(sent_reports[0][1][0].arxiv_id, "2401.00002")
            self.assertIn("2401.00002", sent_reports[0][2])

            saved = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual([record["arxiv_id"] for record in saved["records"]], ["2401.00001", "2401.00002"])

    def test_run_pipeline_skips_analysis_and_email_when_no_new_papers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self._write_config(temp_path)
            history_path = temp_path / "history.json"
            history_path.write_text(
                json.dumps({"schema_version": 1, "records": [{"arxiv_id": "2401.00001"}]}),
                encoding="utf-8",
            )

            dependencies = PipelineDependencies(
                fetch_papers=lambda: [self._paper("2401.00001", "Already Seen")],
                analyze_paper=lambda paper: self.fail("DeepSeek should not be called when no new papers exist."),
                send_report_email=lambda subject, papers, analyses: self.fail("Email should not be sent."),
            )

            result = run_pipeline(config_path=config_path, history_path=history_path, dependencies=dependencies)

            self.assertEqual(result.fetched_count, 1)
            self.assertEqual(result.selected_count, 0)
            self.assertEqual(result.pushed_count, 0)

    def test_run_pipeline_skips_when_run_interval_has_not_elapsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self._write_config(temp_path, run_interval_days=4)
            history_path = temp_path / "history.json"
            history_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "last_email_sent_time": "2024-01-01T00:00:00+00:00",
                        "records": [],
                    }
                ),
                encoding="utf-8",
            )

            dependencies = PipelineDependencies(
                fetch_papers=lambda: self.fail("arXiv should not be called before the interval elapses."),
                analyze_paper=lambda paper: self.fail("DeepSeek should not be called."),
                send_report_email=lambda subject, papers, analyses: self.fail("Email should not be sent."),
            )

            result = run_pipeline(
                config_path=config_path,
                history_path=history_path,
                dependencies=dependencies,
                now=datetime(2024, 1, 4, 0, 0, tzinfo=timezone.utc),
            )

            self.assertTrue(result.skipped)
            self.assertEqual(result.fetched_count, 0)
            self.assertEqual(result.selected_count, 0)
            self.assertEqual(result.pushed_count, 0)

    def test_run_pipeline_runs_when_run_interval_has_elapsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = self._write_config(temp_path, run_interval_days=4)
            history_path = temp_path / "history.json"
            history_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "last_email_sent_time": "2024-01-01T00:00:00+00:00",
                        "records": [],
                    }
                ),
                encoding="utf-8",
            )
            sent_reports: list[tuple[str, list[Paper], dict[str, str]]] = []

            dependencies = PipelineDependencies(
                fetch_papers=lambda: [self._paper("2401.00002", "Fresh Paper One")],
                analyze_paper=lambda paper: f"# Analysis for {paper.arxiv_id}",
                send_report_email=lambda subject, papers, analyses: sent_reports.append((subject, papers, analyses)),
            )

            result = run_pipeline(
                config_path=config_path,
                history_path=history_path,
                dependencies=dependencies,
                now=datetime(2024, 1, 5, 0, 0, tzinfo=timezone.utc),
            )

            self.assertFalse(result.skipped)
            self.assertEqual(result.pushed_count, 1)
            self.assertEqual(len(sent_reports), 1)

            saved = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["last_email_sent_time"], "2024-01-05T00:00:00+00:00")

    def test_main_prints_success_message(self) -> None:
        output = io.StringIO()

        with (
            patch("research_agent.main._configure_logging"),
            patch("research_agent.main.run_pipeline"),
            redirect_stdout(output),
        ):
            main()

        self.assertIn("Pipeline finished successfully.", output.getvalue())

    @staticmethod
    def _write_config(temp_path: Path, max_papers_per_run: int = 3, run_interval_days: int = 1) -> Path:
        config_path = temp_path / "config.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "agent:",
                    f"  max_papers_per_run: {max_papers_per_run}",
                    f"  run_interval_days: {run_interval_days}",
                    "  timezone: UTC",
                    "memory:",
                    f"  history_path: {temp_path / 'history.json'}",
                    "email:",
                    "  subject_prefix: AI Sports Research Update",
                ]
            ),
            encoding="utf-8",
        )
        return config_path

    @staticmethod
    def _paper(arxiv_id: str, title: str) -> Paper:
        return Paper(
            arxiv_id=arxiv_id,
            title=title,
            authors=["Ada Lovelace"],
            abstract="A paper about soccer video understanding.",
            published="2024-01-02T03:04:05+00:00",
            pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        )


if __name__ == "__main__":
    unittest.main()
