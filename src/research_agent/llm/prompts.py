"""Load and render prompt templates."""

from __future__ import annotations

from pathlib import Path


DEFAULT_PAPER_ANALYSIS_PROMPT = Path("prompts/paper_analysis.md")


def load_prompt_template(prompt_path: str | Path = DEFAULT_PAPER_ANALYSIS_PROMPT) -> str:
    """Load a prompt template from disk."""
    return Path(prompt_path).read_text(encoding="utf-8")


def render_prompt(template: str, values: dict[str, str]) -> str:
    """Render a small `{{placeholder}}` prompt template.

    The project prompt files intentionally use simple placeholders so they can
    stay readable without requiring a template engine in the LLM layer.
    """
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered
