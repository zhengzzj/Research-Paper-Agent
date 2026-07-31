"""arXiv paper discovery integration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import yaml

from research_agent.models.paper import Paper


DEFAULT_PROFILE_PATH = Path("config/research_profile.yaml")
DEFAULT_CONFIG_PATH = Path("config/config.yaml")


class ArxivPaperFetcher:
    """Fetch latest arXiv papers for configured research keywords."""

    def __init__(
        self,
        profile_path: str | Path = DEFAULT_PROFILE_PATH,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
        client: Any | None = None,
        search_keywords: list[str] | None = None,
        categories: list[str] | None = None,
        max_results_per_keyword: int | None = None,
    ) -> None:
        self.profile_path = Path(profile_path)
        self.config_path = Path(config_path)

        profile = self._load_yaml(self.profile_path) if search_keywords is None else {}
        config = self._load_yaml(self.config_path) if categories is None or max_results_per_keyword is None else {}
        arxiv_config = config.get("sources", {}).get("arxiv", {})

        self.search_keywords = search_keywords or profile.get("search_keywords", [])
        self.categories = categories if categories is not None else arxiv_config.get("categories", [])
        self.max_results_per_keyword = (
            max_results_per_keyword
            if max_results_per_keyword is not None
            else int(arxiv_config.get("max_results_per_keyword", 20))
        )
        self.sort_by = arxiv_config.get("sort_by", "submittedDate")
        self.sort_order = arxiv_config.get("sort_order", "descending")
        self.client = client or self._create_default_client()

        if not self.search_keywords:
            raise ValueError("No arXiv search keywords configured.")

    def fetch_latest_papers(self) -> list[Paper]:
        """Fetch latest papers and return de-duplicated unified Paper objects."""
        papers_by_id: dict[str, Paper] = {}

        for keyword in self.search_keywords:
            query = self._build_query(keyword)
            search = self._build_search(query)

            for result in self.client.results(search):
                paper = self._paper_from_result(result)
                papers_by_id.setdefault(paper.arxiv_id, paper)

        return list(papers_by_id.values())

    def _build_query(self, keyword: str) -> str:
        keyword_query = f'all:"{keyword}"'
        if not self.categories:
            return keyword_query

        category_query = " OR ".join(f"cat:{category}" for category in self.categories)
        return f"({keyword_query}) AND ({category_query})"

    def _build_search(self, query: str) -> Any:
        arxiv = self._import_arxiv()
        return arxiv.Search(
            query=query,
            max_results=self.max_results_per_keyword,
            sort_by=self._sort_criterion(arxiv),
            sort_order=self._sort_order(arxiv),
        )

    def _paper_from_result(self, result: Any) -> Paper:
        return Paper(
            arxiv_id=self._extract_arxiv_id(result.entry_id),
            title=self._clean_text(result.title),
            authors=[str(author) for author in getattr(result, "authors", [])],
            abstract=self._clean_text(result.summary),
            published=self._format_datetime(result.published),
            pdf_url=getattr(result, "pdf_url", "") or "",
        )

    def _sort_criterion(self, arxiv_module: Any) -> Any:
        mapping = {
            "submittedDate": arxiv_module.SortCriterion.SubmittedDate,
            "lastUpdatedDate": arxiv_module.SortCriterion.LastUpdatedDate,
            "relevance": arxiv_module.SortCriterion.Relevance,
        }
        return mapping.get(self.sort_by, arxiv_module.SortCriterion.SubmittedDate)

    def _sort_order(self, arxiv_module: Any) -> Any:
        if str(self.sort_order).lower() == "ascending":
            return arxiv_module.SortOrder.Ascending
        return arxiv_module.SortOrder.Descending

    @staticmethod
    def _extract_arxiv_id(entry_id: str) -> str:
        raw_id = entry_id.rstrip("/").split("/")[-1]
        return re.sub(r"v\d+$", "", raw_id)

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _format_datetime(value: Any) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected YAML mapping in {path}")
        return loaded

    @staticmethod
    def _create_default_client() -> Any:
        arxiv = ArxivPaperFetcher._import_arxiv()
        return arxiv.Client()

    @staticmethod
    def _import_arxiv() -> Any:
        try:
            import arxiv
        except ImportError as exc:
            raise RuntimeError("The 'arxiv' package is required. Install requirements.txt first.") from exc
        return arxiv


def fetch_latest_papers(
    profile_path: str | Path = DEFAULT_PROFILE_PATH,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> list[Paper]:
    """Convenience function for one-off fetching from repository config."""
    return ArxivPaperFetcher(profile_path=profile_path, config_path=config_path).fetch_latest_papers()


def papers_to_dicts(papers: Iterable[Paper]) -> list[dict[str, object]]:
    """Convert Paper objects to dictionaries for JSON serialization or debugging."""
    return [paper.to_dict() for paper in papers]

