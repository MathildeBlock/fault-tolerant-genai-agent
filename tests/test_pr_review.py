from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APIStatusError

import scripts.analyze_pr as analyze_pr


def test_configured_api_version_rejects_invalid_suffix(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-01-01-not-a-real-version")

    with pytest.raises(RuntimeError, match="YYYY-MM-DD or YYYY-MM-DD-preview"):
        analyze_pr.configured_api_version()


def test_configured_api_version_rejects_older_date(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-10-21-preview")

    with pytest.raises(RuntimeError, match="2024-12-01 or newer"):
        analyze_pr.configured_api_version()


def test_review_diff_handles_empty_choices(monkeypatch):
    class EmptyResponseClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(choices=[])
                )
            )

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "test-deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    monkeypatch.setattr(analyze_pr, "AzureOpenAI", EmptyResponseClient)

    result = analyze_pr.review_diff("diff --git a/example.py b/example.py")

    assert "no review choices" in result


def configure_review_environment(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "test-deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")


def test_review_diff_reports_connection_errors(monkeypatch):
    class FailingClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: (_ for _ in ()).throw(
                        APIConnectionError(
                            request=httpx.Request(
                                "POST", "https://example.openai.azure.com"
                            )
                        )
                    )
                )
            )

    configure_review_environment(monkeypatch)
    monkeypatch.setattr(analyze_pr, "AzureOpenAI", FailingClient)

    with pytest.raises(RuntimeError, match="Could not connect to Azure OpenAI"):
        analyze_pr.review_diff("diff")


def test_review_diff_reports_configuration_errors(monkeypatch):
    class InvalidConfigurationClient:
        def __init__(self, **kwargs):
            raise ValueError("invalid endpoint")

    configure_review_environment(monkeypatch)
    monkeypatch.setattr(analyze_pr, "AzureOpenAI", InvalidConfigurationClient)

    with pytest.raises(RuntimeError, match="configuration error"):
        analyze_pr.review_diff("diff")


def test_review_diff_reports_api_status_errors(monkeypatch):
    class FailingClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: (_ for _ in ()).throw(
                        APIStatusError(
                            "bad request",
                            response=httpx.Response(
                                400,
                                request=httpx.Request(
                                    "POST", "https://example.openai.azure.com"
                                ),
                            ),
                            body={"error": {"message": "invalid request"}},
                        )
                    )
                )
            )

    configure_review_environment(monkeypatch)
    monkeypatch.setattr(analyze_pr, "AzureOpenAI", FailingClient)

    with pytest.raises(RuntimeError, match="HTTP 400"):
        analyze_pr.review_diff("diff")