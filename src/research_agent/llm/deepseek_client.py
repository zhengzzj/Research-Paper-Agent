"""DeepSeek API client wrapper."""

from __future__ import annotations

import json as jsonlib
import os
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen


from research_agent.llm.prompts import DEFAULT_PAPER_ANALYSIS_PROMPT, load_prompt_template, render_prompt
from research_agent.models.paper import Paper


DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


class HttpResponse(Protocol):
    """Minimal response interface used by the DeepSeek client."""

    def raise_for_status(self) -> None:
        """Raise an error for unsuccessful HTTP responses."""

    def json(self) -> dict[str, Any]:
        """Return the response body as JSON."""


class HttpClient(Protocol):
    """Minimal HTTP client interface used for easy testing."""

    def post(self, url: str, headers: dict[str, str], json: dict[str, object]) -> HttpResponse:
        """POST JSON to a URL."""


class UrllibHttpClient:
    """Small standard-library JSON HTTP client."""

    def __init__(self, timeout_seconds: float = 60.0) -> None:
        self.timeout_seconds = timeout_seconds

    def post(self, url: str, headers: dict[str, str], json: dict[str, object]) -> HttpResponse:
        body = jsonlib.dumps(json, ensure_ascii=False).encode("utf-8")
        request = Request(url=url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
                return JsonHttpResponse(status_code=response.status, body=response_body)
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            return JsonHttpResponse(status_code=exc.code, body=error_body)


class JsonHttpResponse:
    """Simple JSON response wrapper."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"DeepSeek API request failed with HTTP {self.status_code}: {self.body}")

    def json(self) -> dict[str, Any]:
        loaded = jsonlib.loads(self.body)
        if not isinstance(loaded, dict):
            raise ValueError("DeepSeek response must be a JSON object.")
        return loaded


class DeepSeekClient:
    """Client for generating paper analyses with DeepSeek."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        api_url: str = DEEPSEEK_API_URL,
        timeout_seconds: float = 60.0,
        http_client: HttpClient | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required.")

        self.model = model
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client or UrllibHttpClient(timeout_seconds=timeout_seconds)

    def analyze_paper(
        self,
        paper: Paper | dict[str, Any],
        paper_content: str | None = None,
        prompt_path: str | Path = DEFAULT_PAPER_ANALYSIS_PROMPT,
    ) -> str:
        """Generate a markdown analysis for one paper."""
        prompt = build_paper_analysis_prompt(paper=paper, paper_content=paper_content, prompt_path=prompt_path)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a rigorous AI research assistant. Return markdown only.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = self.http_client.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return _extract_markdown_content(data)


def analyze_paper(
    paper: Paper | dict[str, Any],
    paper_content: str | None = None,
    prompt_path: str | Path = DEFAULT_PAPER_ANALYSIS_PROMPT,
    client: DeepSeekClient | None = None,
) -> str:
    """Convenience function for generating one paper analysis."""
    deepseek_client = client or DeepSeekClient()
    return deepseek_client.analyze_paper(paper=paper, paper_content=paper_content, prompt_path=prompt_path)


def build_paper_analysis_prompt(
    paper: Paper | dict[str, Any],
    paper_content: str | None = None,
    prompt_path: str | Path = DEFAULT_PAPER_ANALYSIS_PROMPT,
) -> str:
    """Build the prompt sent to DeepSeek from metadata and optional paper text."""
    template = load_prompt_template(prompt_path)
    metadata = _paper_metadata_json(paper)
    content = paper_content or _paper_abstract(paper)
    return render_prompt(
        template,
        {
            "paper_metadata": metadata,
            "paper_content": content,
        },
    )


def _paper_metadata_json(paper: Paper | dict[str, Any]) -> str:
    if isinstance(paper, Paper):
        payload = paper.to_dict()
    else:
        payload = dict(paper)
    return jsonlib.dumps(payload, ensure_ascii=False, indent=2)


def _paper_abstract(paper: Paper | dict[str, Any]) -> str:
    if isinstance(paper, Paper):
        return paper.abstract
    abstract = paper.get("abstract", "")
    return abstract if isinstance(abstract, str) else ""


def _extract_markdown_content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("DeepSeek response did not contain choices[0].message.content.") from exc

    if not isinstance(content, str) or not content.strip():
        raise ValueError("DeepSeek response content is empty.")

    return content.strip()
