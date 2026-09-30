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

## Part 3: AI PR Review Bot

The workflow in `.github/workflows/pr-review.yml` runs when a pull request is opened or updated. It fetches the pull request diff, sends it to the configured Azure OpenAI deployment, and posts one review comment.
The automated review is informational and does not block merging.

Configure these GitHub repository secrets before using the workflow:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_DEPLOYMENT
AZURE_OPENAI_API_VERSION
```

Use API version `2024-12-01-preview` or newer. The review model requires the `max_completion_tokens` parameter supported by that API version.

The workflow uses the built-in `GITHUB_TOKEN` to read the diff and write the comment. Pull requests from forks may not receive repository secrets, so the workflow is intended for pull requests within the repository unless a secure fork-handling design is added.

## Part 4: Terraform Azure Skeleton

The `infra/` folder describes a minimal Azure deployment using a resource group, Linux App Service plan, and Linux Web App. It does not deploy anything by itself and does not create networking, storage accounts, or Key Vault resources.

Validate the Terraform configuration:

```powershell
cd infra
terraform init
terraform validate
```

The default container image is a placeholder. Set `container_image` to an image containing this FastAPI application when using the skeleton for a real deployment.