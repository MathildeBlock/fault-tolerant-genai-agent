"""Analyze a pull request diff and publish one LLM-generated review comment."""

from __future__ import annotations

import os
import sys
from typing import Any

import requests
from openai import APIConnectionError, APIStatusError, AzureOpenAI


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


def review_diff(diff: str) -> str:
    endpoint = required_env("AZURE_OPENAI_ENDPOINT").strip()
    client = AzureOpenAI(
        api_key=required_env("AZURE_OPENAI_API_KEY"),
        azure_endpoint=endpoint,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )
    try:
        response = client.chat.completions.create(
            model=required_env("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You review pull requests. Summarize the change briefly, identify concrete "
                        "bugs or risks, and suggest practical improvements. Keep the review concise."
                    ),
                },
                {"role": "user", "content": f"Review this pull request diff:\n\n{diff}"},
            ],
            max_tokens=1000,
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
    return response.choices[0].message.content or "The model returned an empty review."


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