"""Send HTML email through SMTP using credentials from environment variables."""

from __future__ import annotations

import html
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Protocol

from research_agent.models.paper import Paper


DEFAULT_TEMPLATE_PATH = Path("templates/email_report.html")
DEFAULT_SMTP_PORT = 465
SMTP_HOST_BY_DOMAIN = {
    "126.com": "smtp.126.com",
    "163.com": "smtp.163.com",
    "gmail.com": "smtp.gmail.com",
    "qq.com": "smtp.qq.com",
    "outlook.com": "smtp.office365.com",
    "hotmail.com": "smtp.office365.com",
}


class SmtpConnection(Protocol):
    """Minimal SMTP connection interface used for tests."""

    def __enter__(self) -> "SmtpConnection":
        """Enter context manager."""

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Exit context manager."""

    def login(self, user: str, password: str) -> None:
        """Authenticate with SMTP server."""

    def send_message(self, msg: EmailMessage) -> None:
        """Send an email message."""


def render_email_html(
    subject: str,
    papers: list[Paper | dict[str, Any]] | None = None,
    analyses: dict[str, str] | None = None,
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
) -> str:
    """Render the HTML email body from the repository template."""
    papers = papers or []
    analyses = analyses or {}
    template = Path(template_path).read_text(encoding="utf-8")
    paper_sections = "\n".join(_render_paper_section(paper, analyses) for paper in papers)

    return (
        template.replace("{{subject}}", html.escape(subject))
        .replace("{{paper_count}}", str(len(papers)))
        .replace("{{paper_sections}}", paper_sections)
    )


def send_email(
    subject: str,
    html_body: str,
    to_email: str | None = None,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_factory: Any | None = None,
) -> None:
    """Send one HTML email.

    Credentials are read from `EMAIL_ADDRESS` and `EMAIL_PASSWORD`. The password
    is used only for SMTP login and is never persisted.
    """
    from_email = _required_env("EMAIL_ADDRESS")
    password = _required_env("EMAIL_PASSWORD")
    recipient = to_email or os.getenv("EMAIL_TO") or from_email
    host = smtp_host or os.getenv("EMAIL_SMTP_HOST") or _infer_smtp_host(from_email)
    port = int(smtp_port or os.getenv("EMAIL_SMTP_PORT") or DEFAULT_SMTP_PORT)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = recipient
    message.set_content("This email contains an HTML research paper report.")
    message.add_alternative(html_body, subtype="html")

    factory = smtp_factory or smtplib.SMTP_SSL
    with factory(host, port) as smtp:
        smtp.login(from_email, password)
        smtp.send_message(message)


def send_report_email(
    subject: str,
    papers: list[Paper | dict[str, Any]],
    analyses: dict[str, str] | None = None,
    to_email: str | None = None,
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
    smtp_factory: Any | None = None,
) -> None:
    """Render and send a research report email."""
    html_body = render_email_html(subject=subject, papers=papers, analyses=analyses, template_path=template_path)
    send_email(subject=subject, html_body=html_body, to_email=to_email, smtp_factory=smtp_factory)


def send_test_email(
    to_email: str | None = None,
    smtp_factory: Any | None = None,
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
) -> None:
    """Send a small test email to verify SMTP configuration."""
    subject = "Research Paper Agent SMTP Test"
    html_body = render_email_html(subject=subject, papers=[], template_path=template_path)
    send_email(subject=subject, html_body=html_body, to_email=to_email, smtp_factory=smtp_factory)


def _render_paper_section(paper: Paper | dict[str, Any], analyses: dict[str, str]) -> str:
    metadata = paper.to_dict() if isinstance(paper, Paper) else dict(paper)
    arxiv_id = str(metadata.get("arxiv_id", ""))
    analysis = analyses.get(arxiv_id, "")

    return f"""
    <article>
      <h2>{html.escape(str(metadata.get("title", "")))}</h2>
      <p><strong>Authors:</strong> {html.escape(", ".join(_authors(metadata)))}</p>
      <p><strong>arXiv ID:</strong> {html.escape(arxiv_id)}</p>
      <p><strong>Published:</strong> {html.escape(str(metadata.get("published", "")))}</p>
      <p><strong>PDF:</strong> <a href="{html.escape(str(metadata.get("pdf_url", "")))}">{html.escape(str(metadata.get("pdf_url", "")))}</a></p>
      <h3>Original Abstract</h3>
      <p>{html.escape(str(metadata.get("abstract", "")))}</p>
      <h3>DeepSeek Analysis</h3>
      <pre>{html.escape(analysis)}</pre>
    </article>
    """


def _authors(metadata: dict[str, Any]) -> list[str]:
    authors = metadata.get("authors", [])
    if not isinstance(authors, list):
        return []
    return [str(author) for author in authors]


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required.")
    return value


def _infer_smtp_host(email_address: str) -> str:
    domain = email_address.rsplit("@", 1)[-1].lower()
    if domain in SMTP_HOST_BY_DOMAIN:
        return SMTP_HOST_BY_DOMAIN[domain]
    raise ValueError(
        "EMAIL_SMTP_HOST environment variable is required because the sender email domain "
        f"'{domain}' is not recognized."
    )
