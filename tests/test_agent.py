import httpx
import pytest
from types import SimpleNamespace

from agent.agent import TicketAgent
from agent.client import TicketAPIClient, TicketAPIError, TicketTools


def make_agent(handler):
    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="http://ticket-api", transport=transport)
    return TicketAgent(TicketAPIClient("http://ticket-api", client=client))


def test_agent_reports_invalid_status_from_api():
    def handler(request):
        return httpx.Response(
            422,
            json={"detail": "Invalid status 'PROGRESS'. Valid statuses are: OPEN, RESOLVED, CLOSED."},
        )

    agent = make_agent(handler)
    response = agent.respond("Update ticket 12345678-1234-1234-1234-123456789abc to PROGRESS")
    assert "PROGRESS" in response
    assert "OPEN, RESOLVED, CLOSED" in response


def test_agent_reports_missing_ticket_from_api():
    def handler(request):
        return httpx.Response(404, json={"detail": "Ticket with id 'missing' not found."})

    agent = make_agent(handler)
    response = agent.respond("Get details for ticket 12345678-1234-1234-1234-123456789abc")
    assert "could not find" in response.lower()


def test_agent_lists_open_tickets():
    def handler(request):
        assert request.url.path == "/tickets"
        assert request.url.params["status"] == "OPEN"
        return httpx.Response(200, json=[{"id": "1", "title": "Keyboard", "status": "OPEN"}])

    agent = make_agent(handler)
    assert "Keyboard" in agent.respond("Retrieve all open tickets")


def test_agent_passes_resolution_text_without_trailing_phrase():
    def handler(request):
        assert request.url.path.endswith("/12345678-1234-1234-1234-123456789abc")
        payload = request.read()
        assert b'"resolution":"Replaced faulty cable"' in payload
        return httpx.Response(
            200,
            json={"id": "12345678-1234-1234-1234-123456789abc", "status": "RESOLVED"},
        )

    agent = make_agent(handler)
    response = agent.respond(
        "Update ticket 12345678-1234-1234-1234-123456789abc to be RESOLVED, "
        "adding 'Replaced faulty cable' as the resolution."
    )
    assert "RESOLVED" in response


def test_agent_handles_non_uuid_ticket_id():
    def handler(request):
        assert request.url.path == "/tickets/non-existent-id"
        return httpx.Response(404, json={"detail": "Ticket with id 'non-existent-id' not found."})

    agent = make_agent(handler)
    response = agent.respond("Update ticket non-existent-id to CLOSED")
    assert "could not find" in response.lower()
    assert "non-existent-id" in response


def test_llm_agent_disables_reasoning_for_chat_tools():
    calls = []

    class MockLLM:
        class Chat:
            class Completions:
                @staticmethod
                def create(**kwargs):
                    calls.append(kwargs)
                    return SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(content="Done", tool_calls=None)
                            )
                        ]
                    )

            def __init__(self):
                self.completions = self.Completions()

        chat = Chat()

    agent = make_agent(lambda request: httpx.Response(200, json={}))
    agent.llm_client = MockLLM()

    assert agent.respond("List my tickets") == "Done"
    assert calls[0]["reasoning_effort"] == "none"


def test_update_tool_leaves_status_validation_to_api():
    update_tool = next(
        tool for tool in TicketTools.definitions()
        if tool["function"]["name"] == "update_ticket"
    )
    status_schema = update_tool["function"]["parameters"]["properties"]["status"]

    assert "enum" not in status_schema


def test_client_reports_empty_success_response():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b""))
    client = httpx.Client(base_url="http://ticket-api", transport=transport)
    api = TicketAPIClient("http://ticket-api", client=client)

    with pytest.raises(TicketAPIError, match="empty or invalid JSON"):
        api.update_ticket("ticket-id", status="RESOLVED")