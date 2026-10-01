# fault-tolerant-genai-agent

## Prerequisites and Setup

Install Python 3.11 or newer. From the repository root, create the virtual environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

PowerShell activation is optional; all commands below use the virtual environment directly. Copy `env.example` to `.env` only if you want to use Azure OpenAI model-driven mode:

```powershell
Copy-Item env.example .env
```

Keep the real API key in `.env` only. The local CLI mode and automated tests do not require an Azure OpenAI key.

Azure OpenAI is optional. Set `AZURE_OPENAI_REASONING_EFFORT` only when your deployment supports a supported reasoning value such as `low`, `medium`, or `high`; otherwise leave it unset.

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

The workflow in `.github/workflows/pr-review.yml` runs when a pull request is opened or updated. It fetches the pull request diff, sends it to Azure OpenAI, and posts one review comment.

The workflow expects these GitHub repository secrets to be configured:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_DEPLOYMENT
AZURE_OPENAI_API_VERSION
```

Very large diffs are truncated before they are sent to the model, and the review is informational only.

## Part 4: Terraform Azure Skeleton

The `infra/` folder contains a minimal Azure App Service scaffold. It validates as a Terraform project, but it is not a complete production deployment.

Validate it with:

```powershell
cd infra
terraform init
terraform validate
```

The default image is a placeholder nginx container, so this is not yet a live deployment of the FastAPI app. For a real deployment, replace `container_image` and `container_port` with values for the application image.

For `terraform plan` or `terraform apply`, AzureRM requires a subscription ID. After `az login`, set it in the current PowerShell session:

```powershell
$env:ARM_SUBSCRIPTION_ID = (az account show --query id -o tsv)
```

## Part 5: Production Design Decision

For production, I would replace the in-memory ticket storage with a persistent database. The current API loses all tickets whenever it restarts, so durable storage would be the most important improvement.