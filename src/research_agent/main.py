"""MVP workflow entry point."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import yaml

from research_agent.email.sender import send_report_email
from research_agent.llm.deepseek_client import DeepSeekClient
from research_agent.memory.history import add_paper, is_duplicate, load_history
from research_agent.models.paper import Paper
from research_agent.sources.arxiv import ArxivPaperFetcher


DEFAULT_CONFIG_PATH = Path("config/config.yaml")
DEFAULT_PROFILE_PATH = Path("config/research_profile.yaml")

logger = logging.getLogger(__name__)


FetchPapers = Callable[[], list[Paper]]
AnalyzePaper = Callable[[Paper], str]
SendReportEmail = Callable[[str, list[Paper], dict[str, str]], None]


@dataclass(frozen=True)
class PipelineDependencies:
    """External side effects used by the pipeline.

    Tests can provide fakes here so the MVP flow can be verified without calling
    arXiv, DeepSeek, or SMTP.
    """

    fetch_papers: FetchPapers | None = None
    analyze_paper: AnalyzePaper | None = None
    send_report_email: SendReportEmail | None = None


@dataclass(frozen=True)
class PipelineResult:
    """Summary of one pipeline run."""

    fetched_count: int
    selected_count: int
    pushed_count: int


def run_pipeline(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    profile_path: str | Path = DEFAULT_PROFILE_PATH,
    history_path: str | Path | None = None,
    dependencies: PipelineDependencies | None = None,
) -> PipelineResult:
    """Run one MVP research paper recommendation cycle."""
    dependencies = dependencies or PipelineDependencies()
    config = _load_config(config_path)
    resolved_history_path = Path(history_path or config.get("memory", {}).get("history_path", "data/history.json"))
    max_papers = int(config.get("agent", {}).get("max_papers_per_run", 3))

    logger.info("Starting Research Paper Agent MVP pipeline.")
    logger.info("Loading history from %s.", resolved_history_path)
    history = load_history(resolved_history_path)

    fetch_papers = dependencies.fetch_papers or _default_fetch_papers(config_path, profile_path)
    logger.info("Fetching arXiv candidate papers.")
    candidates = fetch_papers()
    logger.info("Fetched %d candidate papers.", len(candidates))

    fresh_papers = [paper for paper in candidates if not is_duplicate(paper, history)]
    logger.info("Filtered %d duplicate papers by exact arXiv ID.", len(candidates) - len(fresh_papers))

    selected_papers = fresh_papers[:max_papers]
    logger.info("Selected %d papers for analysis.", len(selected_papers))

    if not selected_papers:
        logger.info("No new papers selected. Skipping DeepSeek analysis, email, and history update.")
        return PipelineResult(fetched_count=len(candidates), selected_count=0, pushed_count=0)

    analyze_paper = dependencies.analyze_paper or _default_analyze_paper()
    analyses: dict[str, str] = {}
    for paper in selected_papers:
        logger.info("Analyzing paper with DeepSeek: %s (%s).", paper.title, paper.arxiv_id)
        analyses[paper.arxiv_id] = analyze_paper(paper)

    subject = _email_subject(config)
    send_email = dependencies.send_report_email or send_report_email
    logger.info("Sending report email with subject: %s.", subject)
    send_email(subject, selected_papers, analyses)

    pushed_count = 0
    logger.info("Updating history after successful email delivery.")
    for paper in selected_papers:
        if add_paper(paper, history_path=resolved_history_path):
            pushed_count += 1

    logger.info("Pipeline completed. Added %d papers to history.", pushed_count)
    return PipelineResult(
        fetched_count=len(candidates),
        selected_count=len(selected_papers),
        pushed_count=pushed_count,
    )


def main() -> None:
    """Run one scheduled agent cycle."""
    _configure_logging()
    run_pipeline()
    print("Pipeline finished successfully.")


def _default_fetch_papers(config_path: str | Path, profile_path: str | Path) -> FetchPapers:
    fetcher = ArxivPaperFetcher(config_path=config_path, profile_path=profile_path)
    return fetcher.fetch_latest_papers


def _default_analyze_paper() -> AnalyzePaper:
    client = DeepSeekClient()
    return client.analyze_paper


def _load_config(config_path: str | Path) -> dict[str, Any]:
    with Path(config_path).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    if not isinstance(config, dict):
        raise ValueError(f"Expected YAML mapping in {config_path}")
    return config


def _email_subject(config: dict[str, Any]) -> str:
    email_config = config.get("email", {})
    agent_config = config.get("agent", {})
    prefix = email_config.get("subject_prefix", "AI Sports Research Update")
    timezone_name = agent_config.get("timezone", "UTC")
    today = datetime.now(ZoneInfo(timezone_name)).date().isoformat()
    return f"{prefix} {today}"


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


if __name__ == "__main__":
    main()
