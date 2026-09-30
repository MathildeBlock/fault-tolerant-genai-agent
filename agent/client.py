"""HTTP client and tool definitions for the mock ticketing API."""

from __future__ import annotations

from typing import Any

import httpx


class TicketAPIError(Exception):
    """A business or transport error returned by the ticketing API."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)

    def user_message(self) -> str:
        """Turn API validation details into actionable agent feedback."""
        if self.status_code == 404:
            return f"I could not find that ticket. {self.detail}"
        if self.status_code == 422:
            return f"I could not update the ticket because the request is invalid. {self.detail}"
        return f"The ticketing API returned an error ({self.status_code}). {self.detail}"


class TicketAPIClient:
    """Small client exposing each supported ticketing operation."""

    def __init__(self, base_url: str, client: httpx.Client | None = None):
        self._client = client or httpx.Client(base_url=base_url.rstrip("/"), timeout=10.0)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise TicketAPIError(503, f"The ticketing API is unavailable: {exc}") from exc

        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise TicketAPIError(response.status_code, str(detail))
        if response.status_code == 204:
            return None
        return response.json()

    def create_ticket(self, title: str, description: str) -> dict[str, Any]:
        return self._request("POST", "/tickets", json={"title": title, "description": description})

    def list_tickets(
        self, status: str | None = None, has_resolution: bool | None = None
    ) -> list[dict[str, Any]]:
        params = {}
        if status is not None:
            params["status"] = status
        if has_resolution is not None:
            params["has_resolution"] = has_resolution
        return self._request("GET", "/tickets", params=params)

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        return self._request("GET", f"/tickets/{ticket_id}")

    def update_ticket(self, ticket_id: str, **fields: Any) -> dict[str, Any]:
        return self._request("PATCH", f"/tickets/{ticket_id}", json=fields)

    def delete_ticket(self, ticket_id: str) -> None:
        self._request("DELETE", f"/tickets/{ticket_id}")


class TicketTools:
    """Tool registry used by the local parser or an LLM function-calling loop."""

    def __init__(self, api: TicketAPIClient):
        self.api = api

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = getattr(self.api, name)
        return tool(**arguments)

    @staticmethod
    def definitions() -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_ticket",
                    "description": "Create a new support ticket.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["title", "description"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tickets",
                    "description": "List tickets, optionally filtered by status or resolution.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["OPEN", "RESOLVED", "CLOSED"]},
                            "has_resolution": {"type": "boolean"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_ticket",
                    "description": "Retrieve one ticket by ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {"ticket_id": {"type": "string"}},
                        "required": ["ticket_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_ticket",
                    "description": "Update ticket fields, status, resolution, or add a comment.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "status": {"type": "string", "enum": ["OPEN", "RESOLVED", "CLOSED"]},
                            "resolution": {"type": "string"},
                            "comment": {"type": "string"},
                        },
                        "required": ["ticket_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_ticket",
                    "description": "Delete a ticket by ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {"ticket_id": {"type": "string"}},
                        "required": ["ticket_id"],
                    },
                },
            },
        ]