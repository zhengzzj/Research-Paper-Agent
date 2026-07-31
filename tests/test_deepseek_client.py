"""Tests for DeepSeek paper analysis client."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_agent.llm.deepseek_client import DeepSeekClient, build_paper_analysis_prompt
from research_agent.models.paper import Paper


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


class FakeHttpClient:
    def __init__(self) -> None:
        self.last_url: str | None = None
        self.last_headers: dict[str, str] | None = None
        self.last_json: dict[str, object] | None = None

    def post(self, url: str, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
        self.last_url = url
        self.last_headers = headers
        self.last_json = json
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "# 一句话总结\n\n这是一篇足球视频理解论文。"
                        }
                    }
                ]
            }
        )


class DeepSeekClientTests(unittest.TestCase):
    def test_build_paper_analysis_prompt_uses_metadata_and_prompt_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_path = Path(temp_dir) / "paper_analysis.md"
            prompt_path.write_text(
                "Paper metadata:\n{{paper_metadata}}\n\nContent:\n{{paper_content}}\n",
                encoding="utf-8",
            )

            prompt = build_paper_analysis_prompt(self._paper(), prompt_path=prompt_path)

            self.assertIn('"arxiv_id": "2401.12345"', prompt)
            self.assertIn("Soccer Video Understanding with Multimodal Agents", prompt)
            self.assertIn("A paper about soccer video understanding.", prompt)

    def test_client_reads_api_key_from_environment_and_returns_markdown(self) -> None:
        fake_http = FakeHttpClient()

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-api-key"}):
            client = DeepSeekClient(http_client=fake_http)
            result = client.analyze_paper(self._paper(), prompt_path=self._prompt_path())

        self.assertEqual(result, "# 一句话总结\n\n这是一篇足球视频理解论文。")
        self.assertEqual(fake_http.last_headers["Authorization"], "Bearer test-api-key")
        self.assertEqual(fake_http.last_json["model"], "deepseek-chat")
        self.assertEqual(fake_http.last_json["messages"][1]["role"], "user")

    def test_client_requires_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DEEPSEEK_API_KEY"):
                DeepSeekClient()

    @staticmethod
    def _paper() -> Paper:
        return Paper(
            arxiv_id="2401.12345",
            title="Soccer Video Understanding with Multimodal Agents",
            authors=["Ada Lovelace", "Alan Turing"],
            abstract="A paper about soccer video understanding.",
            published="2024-01-02T03:04:05+00:00",
            pdf_url="https://arxiv.org/pdf/2401.12345v2",
        )

    @staticmethod
    def _prompt_path() -> Path:
        return Path("prompts/paper_analysis.md")


if __name__ == "__main__":
    unittest.main()
