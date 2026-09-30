# fault-tolerant-genai-agent

## Part 1: Mock API

From the repository root, start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

The interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Part 2: Ticket Agent

With the API running in another terminal, start the CLI:

```powershell
.\.venv\Scripts\python.exe -m agent.cli
```

The agent works locally without an LLM key. Set the Azure OpenAI values from `env.example` in a local `.env` file to enable model-driven tool calling. The agent exposes create, list/filter, get, update, and delete operations and relays API validation details to the user.

Example requests:

```text
Create a new ticket about a keyboard not working.
Retrieve all open tickets.
Get details for ticket <ticket-id>.
Update ticket <ticket-id> to have the status 'PROGRESS'.
Update ticket <ticket-id> to be RESOLVED, adding 'Replaced faulty cable' as the resolution.
```

Run the tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```