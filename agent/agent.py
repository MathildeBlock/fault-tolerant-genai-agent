"""Natural-language ticket agent with optional OpenAI tool calling."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAIError

from .client import TicketAPIClient, TicketAPIError, TicketTools


SYSTEM_PROMPT = """You are a support-ticket assistant. Use the ticket tools for every ticket operation.
Never invent ticket data. When a tool returns an error, explain its detail clearly and tell the user
what they can do next. Valid statuses are OPEN, RESOLVED, and CLOSED. Do not silently translate or
normalize an unsupported status such as PROGRESS; pass the user's status to the update tool so the
ticket API can validate it and return its actionable error message."""


class TicketAgent:
    """Orchestrate ticket tools locally, or through an optional OpenAI-compatible model."""

    def __init__(self, api: TicketAPIClient, llm_client: Any | None = None, model: str | None = None):
        self.tools = TicketTools(api)
        self.llm_client = llm_client
        self.model = model or os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def respond(self, request: str) -> str:
        if self.llm_client is not None:
            return self._respond_with_llm(request)
        return self._respond_locally(request)

    def _get_reasoning_effort(self) -> str | None:
        override = os.getenv("AZURE_OPENAI_REASONING_EFFORT")
        if override is None:
            return None

        value = override.strip().lower()
        if value in {"", "false", "0", "off", "no", "none"}:
            return None

        valid_values = {"low", "medium", "high"}
        if value not in valid_values:
            raise ValueError(
                "AZURE_OPENAI_REASONING_EFFORT must be one of: low, medium, high. "
                "Leave it unset or set it to false to disable it."
            )
        return value

    def _respond_with_llm(self, request: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request},
        ]
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": TicketTools.definitions(),
            "tool_choice": "auto",
        }
        try:
            reasoning_effort = self._get_reasoning_effort()
        except ValueError as exc:
            return f"Azure OpenAI configuration error: {exc}"
        if reasoning_effort is not None:
            request_kwargs["reasoning_effort"] = reasoning_effort

        for _ in range(5):
            try:
                response = self.llm_client.chat.completions.create(**request_kwargs)
            except OpenAIError as exc:
                return f"The language model request failed: {exc}"
            message = response.choices[0].message
            if not message.tool_calls:
                return message.content or "I could not produce a response."
            messages.append(message.model_dump())
            for call in message.tool_calls:
                try:
                    result = self.tools.execute(call.function.name, json.loads(call.function.arguments))
                except TicketAPIError as exc:
                    result = {"error": exc.user_message()}
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
                )
        return "I could not complete the request within the tool-call limit."

    def _respond_locally(self, request: str) -> str:
        text = request.strip()
        lowered = text.lower()
        try:
            if lowered.startswith("create"):
                description = text.split(" about ", 1)[1] if " about " in lowered else text
                ticket = self.tools.execute(
                    "create_ticket", {"title": description, "description": description}
                )
                return f"Created ticket {ticket['id']} with status OPEN."

            if "retrieve all open" in lowered or "list all open" in lowered:
                tickets = self.tools.execute("list_tickets", {"status": "OPEN"})
                return self._format_tickets(tickets)

            ticket_id = self._ticket_id(text)
            if ticket_id is None:
                return "Please provide a ticket ID for that request."
            if lowered.startswith("get") or "details" in lowered:
                return json.dumps(self.tools.execute("get_ticket", {"ticket_id": ticket_id}), indent=2)

            if lowered.startswith("delete"):
                self.tools.execute("delete_ticket", {"ticket_id": ticket_id})
                return f"Deleted ticket {ticket_id}."

            status_match = re.search(r"\b(OPEN|RESOLVED|CLOSED|PROGRESS)\b", text, re.IGNORECASE)
            if status_match:
                status = status_match.group(1).upper()
                arguments: dict[str, Any] = {"ticket_id": ticket_id, "status": status}
                resolution_match = re.search(
                    r"adding\s+['\"]([^'\"]+)['\"](?:\s+as\s+the\s+resolution)?",
                    text,
                    re.IGNORECASE,
                )
                if resolution_match:
                    arguments["resolution"] = resolution_match.group(1).strip()
                updated = self.tools.execute("update_ticket", arguments)
                return f"Updated ticket {updated['id']} to {updated['status']}."
        except TicketAPIError as exc:
            return exc.user_message()
        return "I could not match that request to a ticket operation."

    @staticmethod
    def _ticket_id(text: str) -> str | None:
        match = re.search(r"\bticket\s+([A-Za-z0-9][A-Za-z0-9_-]*)", text, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"[0-9a-f]{8}-[0-9a-f-]{27,}", text, re.IGNORECASE)
        return match.group(0) if match else None

    @staticmethod
    def _format_tickets(tickets: list[dict[str, Any]]) -> str:
        if not tickets:
            return "No tickets matched that filter."
        return "\n".join(f"{ticket['id']}: {ticket['title']} ({ticket['status']})" for ticket in tickets)


def create_configured_agent(api: TicketAPIClient) -> TicketAgent:
    """Create an LLM-backed agent when credentials are configured, otherwise use local mode."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key or api_key == "your-key-here":
        return TicketAgent(api)

    from openai import AzureOpenAI

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )
    return TicketAgent(api, llm_client=client)