"""Analyze a pull request diff and publish one LLM-generated review comment."""

from __future__ import annotations

import os
import re
import sys
from datetime import date
from typing import Any

import requests
from openai import APIConnectionError, APIStatusError, AzureOpenAI, OpenAIError

MINIMUM_AZURE_API_DATE = date(2024, 12, 1)
API_VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(?:-preview)?$")


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def github_request(method: str, url: str, token: str, **kwargs: Any) -> requests.Response:
    headers = kwargs.pop("headers", {})
    headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    response.raise_for_status()
    return response


def configured_api_version() -> str:
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview").strip()
    if not API_VERSION_PATTERN.fullmatch(api_version):
        raise RuntimeError(
            "AZURE_OPENAI_API_VERSION must use YYYY-MM-DD or YYYY-MM-DD-preview format."
        )
    try:
        version_date = date.fromisoformat(api_version[:10])
    except ValueError as exc:
        raise RuntimeError(
            "AZURE_OPENAI_API_VERSION must start with a valid YYYY-MM-DD date."
        ) from exc
    if version_date < MINIMUM_AZURE_API_DATE:
        raise RuntimeError(
            "AZURE_OPENAI_API_VERSION must be 2024-12-01 or newer because this "
            "review uses max_completion_tokens."
        )
    return api_version


def review_diff(diff: str) -> str:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "<missing>").strip()
    try:
        client = AzureOpenAI(
            api_key=required_env("AZURE_OPENAI_API_KEY"),
            azure_endpoint=required_env("AZURE_OPENAI_ENDPOINT").strip(),
            api_version=configured_api_version(),
        )
        response = client.chat.completions.create(
            model=required_env("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You review pull requests. Summarize the change briefly, identify concrete "
                        "bugs or risks, and suggest practical improvements. Keep the review concise. "
                        "Return the review as visible plain text with headings and bullet points."
                    ),
                },
                {"role": "user", "content": f"Review this pull request diff:\n\n{diff}"},
            ],
            max_completion_tokens=3000,
        )
    except APIConnectionError as exc:
        raise RuntimeError(
            f"Could not connect to Azure OpenAI endpoint {endpoint!r}. "
            "Check that the endpoint secret is the exact HTTPS URL without quotes. "
            f"Underlying error: {exc}"
        ) from exc
    except APIStatusError as exc:
        response_detail = getattr(exc, "response", None)
        detail = response_detail.text if response_detail is not None else str(exc)
        raise RuntimeError(
            f"Azure OpenAI rejected the request with HTTP {exc.status_code}. "
            f"Response: {detail}"
        ) from exc
    except (OpenAIError, RuntimeError, TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Azure OpenAI configuration error for endpoint {endpoint!r}: {exc}"
        ) from exc
    if not response.choices:
        return "The model returned no review choices. Please review the diff manually."
    message = response.choices[0].message
    if message.content and message.content.strip():
        return message.content.strip()
    refusal = getattr(message, "refusal", None)
    if refusal:
        return f"The model declined to review this diff: {refusal}"
    return "The model returned no visible review text. Please review the diff manually."


def main() -> None:
    token = required_env("GITHUB_TOKEN")
    diff_url = required_env("PR_DIFF_URL")
    comment_url = required_env("PR_COMMENT_URL")

    diff_response = github_request(
        "GET",
        diff_url,
        token,
        headers={"Accept": "application/vnd.github.v3.diff"},
    )
    review = review_diff(diff_response.text)
    comment = f"## Automated PR Review\n\n{review}"
    github_request("POST", comment_url, token, json={"body": comment})
    print("Posted one automated PR review comment.")


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        print(f"PR review failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc