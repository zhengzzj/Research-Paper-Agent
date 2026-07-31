"""Backward-compatible imports for the arXiv source module."""

from research_agent.sources.arxiv import ArxivPaperFetcher, fetch_latest_papers, papers_to_dicts

__all__ = ["ArxivPaperFetcher", "fetch_latest_papers", "papers_to_dicts"]
