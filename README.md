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

The workflow does not run on ordinary branch pushes. To test it, push the workflow to GitHub and open a pull request, or push another commit to an existing pull request. Check the repository's **Actions** tab for the run and the pull request for the generated comment.

Very large pull request diffs are capped before they are sent to the model. The generated comment is explicitly marked as incomplete when truncation occurs.

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

Terraform is only required for this validation step; it does not deploy resources. Run `terraform init` before `terraform validate` so the AzureRM and Random providers are downloaded.

The default container image is a public placeholder nginx image listening on port 80. The skeleton does not configure private registry credentials; add registry configuration before using a private image. Set `container_image` and `container_port` to values matching an image containing this FastAPI application for a real deployment. Terraform uses a short generated App Service plan name and adds a 12-character random suffix to the Web App name, substantially reducing collisions while respecting Azure naming limits.

With the default nginx image, the `api_url` Terraform output is only the URL of the placeholder Web App; it is not a functioning deployment of this FastAPI API until `container_image` is replaced with an image containing the application.

Custom `app_name` values must be 2-47 characters using lowercase letters, numbers, or hyphens. They cannot start or end with a hyphen. The Terraform validation also requires `container_port` to be an integer from 1 through 65535.

For `terraform plan` or `terraform apply`, AzureRM v4 requires a subscription ID. After `az login`, set it for the current PowerShell session:

```powershell
$env:ARM_SUBSCRIPTION_ID = (az account show --query id -o tsv)
```

You can also provide it directly with `-var="subscription_id=<your-subscription-id>"`. `terraform validate` does not require Azure credentials.


## Part 5: Production Design Decision

For production, I would replace the in-memory ticket storage with a persistent database. The current API loses all tickets whenever it restarts, so durable storage would be the most important improvement.