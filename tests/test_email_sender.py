"""Tests for SMTP email sending."""

from __future__ import annotations

import os
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

from research_agent.email.sender import render_email_html, send_report_email, send_test_email
from research_agent.models.paper import Paper


class FakeSmtpConnection:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.login_user: str | None = None
        self.login_password: str | None = None
        self.sent_message: EmailMessage | None = None

    def __enter__(self) -> "FakeSmtpConnection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def login(self, user: str, password: str) -> None:
        self.login_user = user
        self.login_password = password

    def send_message(self, msg: EmailMessage) -> None:
        self.sent_message = msg


class FakeSmtpFactory:
    def __init__(self) -> None:
        self.connection: FakeSmtpConnection | None = None

    def __call__(self, host: str, port: int) -> FakeSmtpConnection:
        self.connection = FakeSmtpConnection(host, port)
        return self.connection


class EmailSenderTests(unittest.TestCase):
    def test_render_email_html_uses_template_and_paper_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "email_report.html"
            template_path.write_text(
                "<h1>{{subject}}</h1><p>{{paper_count}}</p>{{paper_sections}}",
                encoding="utf-8",
            )

            html = render_email_html(
                subject="AI Sports Research Update 2024-01-02",
                papers=[self._paper()],
                analyses={"2401.12345": "# 一句话总结\n很相关。"},
                template_path=template_path,
            )

            self.assertIn("AI Sports Research Update 2024-01-02", html)
            self.assertIn("<p>1</p>", html)
            self.assertIn("Soccer Video Understanding with Multimodal Agents", html)
            self.assertIn("# 一句话总结", html)

    def test_send_report_email_reads_credentials_from_environment(self) -> None:
        smtp_factory = FakeSmtpFactory()

        with patch.dict(
            os.environ,
            {
                "EMAIL_ADDRESS": "sender@example.com",
                "EMAIL_PASSWORD": "secret-password",
                "EMAIL_TO": "receiver@example.com",
                "EMAIL_SMTP_HOST": "smtp.example.com",
                "EMAIL_SMTP_PORT": "465",
            },
        ):
            send_report_email(
                subject="AI Sports Research Update 2024-01-02",
                papers=[self._paper()],
                analyses={"2401.12345": "markdown analysis"},
                smtp_factory=smtp_factory,
            )

        self.assertIsNotNone(smtp_factory.connection)
        connection = smtp_factory.connection
        self.assertEqual(connection.host, "smtp.example.com")
        self.assertEqual(connection.port, 465)
        self.assertEqual(connection.login_user, "sender@example.com")
        self.assertEqual(connection.login_password, "secret-password")
        self.assertEqual(connection.sent_message["To"], "receiver@example.com")
        self.assertEqual(connection.sent_message["From"], "sender@example.com")

    def test_send_test_email_uses_default_test_subject(self) -> None:
        smtp_factory = FakeSmtpFactory()

        with patch.dict(os.environ, {"EMAIL_ADDRESS": "sender@gmail.com", "EMAIL_PASSWORD": "secret-password"}):
            send_test_email(to_email="receiver@example.com", smtp_factory=smtp_factory)

        self.assertEqual(smtp_factory.connection.sent_message["Subject"], "Research Paper Agent SMTP Test")
        self.assertEqual(smtp_factory.connection.sent_message["To"], "receiver@example.com")

    def test_send_email_infers_126_smtp_host_from_sender_address(self) -> None:
        smtp_factory = FakeSmtpFactory()

        with patch.dict(
            os.environ,
            {"EMAIL_ADDRESS": "sender@126.com", "EMAIL_PASSWORD": "secret-password"},
            clear=True,
        ):
            send_test_email(to_email="receiver@qq.com", smtp_factory=smtp_factory)

        self.assertEqual(smtp_factory.connection.host, "smtp.126.com")
        self.assertEqual(smtp_factory.connection.port, 465)

    def test_send_email_requires_password_environment_variable(self) -> None:
        smtp_factory = FakeSmtpFactory()

        with patch.dict(os.environ, {"EMAIL_ADDRESS": "sender@example.com"}, clear=True):
            with self.assertRaisesRegex(ValueError, "EMAIL_PASSWORD"):
                send_test_email(to_email="receiver@example.com", smtp_factory=smtp_factory)

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


if __name__ == "__main__":
    unittest.main()
