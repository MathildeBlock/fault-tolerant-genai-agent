from types import SimpleNamespace

import pytest

import scripts.analyze_pr as analyze_pr


def test_configured_api_version_rejects_invalid_suffix(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-01-01-not-a-real-version")

    with pytest.raises(RuntimeError, match="YYYY-MM-DD or YYYY-MM-DD-preview"):
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