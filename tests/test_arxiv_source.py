"""Tests for arXiv paper fetching."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from research_agent.sources.arxiv import ArxivPaperFetcher, papers_to_dicts


@dataclass(frozen=True)
class FakeAuthor:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class FakeResult:
    entry_id: str
    title: str
    authors: list[FakeAuthor]
    summary: str
    published: datetime
    pdf_url: str


class FakeClient:
    def __init__(self, results_by_query: dict[str, list[FakeResult]]) -> None:
        self.results_by_query = results_by_query

    def results(self, search: dict[str, Any]) -> list[FakeResult]:
        return self.results_by_query.get(search["query"], [])


class TestableArxivPaperFetcher(ArxivPaperFetcher):
    def _build_search(self, query: str) -> dict[str, Any]:
        return {"query": query, "max_results": self.max_results_per_keyword}


class ArxivPaperFetcherTests(unittest.TestCase):
    def test_fetch_latest_papers_returns_normalized_papers(self) -> None:
        query = '(all:"soccer video understanding") AND (cat:cs.CV OR cat:cs.AI)'
        fake_result = FakeResult(
            entry_id="https://arxiv.org/abs/2401.12345v2",
            title="  Soccer Video   Understanding with Multimodal Agents ",
            authors=[FakeAuthor("Ada Lovelace"), FakeAuthor("Alan Turing")],
            summary="A paper about\nsoccer video understanding.",
            published=datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            pdf_url="https://arxiv.org/pdf/2401.12345v2",
        )

        fetcher = TestableArxivPaperFetcher(
            client=FakeClient({query: [fake_result]}),
            search_keywords=["soccer video understanding"],
            categories=["cs.CV", "cs.AI"],
            max_results_per_keyword=5,
        )

        papers = fetcher.fetch_latest_papers()

        self.assertEqual(len(papers), 1)
        self.assertEqual(
            papers_to_dicts(papers)[0],
            {
                "arxiv_id": "2401.12345",
                "title": "Soccer Video Understanding with Multimodal Agents",
                "authors": ["Ada Lovelace", "Alan Turing"],
                "abstract": "A paper about soccer video understanding.",
                "published": "2024-01-02T03:04:05+00:00",
                "pdf_url": "https://arxiv.org/pdf/2401.12345v2",
            },
        )

    def test_fetch_latest_papers_deduplicates_by_arxiv_id(self) -> None:
        keyword_one_query = '(all:"video agent") AND (cat:cs.CV)'
        keyword_two_query = '(all:"multimodal LLM") AND (cat:cs.CV)'
        repeated_paper = FakeResult(
            entry_id="https://arxiv.org/abs/2402.00001v1",
            title="Video Agents for Sports",
            authors=[FakeAuthor("Grace Hopper")],
            summary="A repeated candidate.",
            published=datetime(2024, 2, 1, tzinfo=timezone.utc),
            pdf_url="https://arxiv.org/pdf/2402.00001v1",
        )

        fetcher = TestableArxivPaperFetcher(
            client=FakeClient(
                {
                    keyword_one_query: [repeated_paper],
                    keyword_two_query: [repeated_paper],
                }
            ),
            search_keywords=["video agent", "multimodal LLM"],
            categories=["cs.CV"],
            max_results_per_keyword=5,
        )

        papers = fetcher.fetch_latest_papers()

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].arxiv_id, "2402.00001")


if __name__ == "__main__":
    unittest.main()

