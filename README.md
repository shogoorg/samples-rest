# samples-rest

A hybrid project containing a ReAct shopping agent (built with Google ADK) and a UCP (Universal Commerce Protocol) Merchant Server.

## Project Structure

```
samples-rest/
├── app/                       # Core ADK agent code
│   ├── agent.py               # Main agent logic (customized Flower Shop assistant)
│   └── app_utils/             # App utilities and helpers
├── rest/                      # UCP/REST integration code
│   └── python/
│       ├── client/            # UCP client verification scripts (Flower Shop)
│       ├── test_data/         # CSV test data (products, discounts, etc.)
│       └── server/            # UCP Merchant Server (FastAPI)
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)

## Quick Start

### 1. Run the ADK Agent (Shopping Assistant)

This agent simulates a full customer shopping checkout flow referencing the **A2A (Agent-to-Agent)** shopping protocol.

Install `agents-cli` and its skills if not already installed:

```bash
uvx google-agents-cli setup
```

Install required packages:

```bash
agents-cli install
```

Start the interactive development playground:

```bash
agents-cli playground
```

Or test the agent directly from your terminal using commands to run through the entire shopping flow:

```bash
# 1. Search for flowers in catalog (calls 'search_products')
agents-cli run "Show me roses in stock"

# 2. Add product to checkout cart (calls 'add_to_checkout')
agents-cli run "Add bouquet_roses to my checkout"

# 3. Save shipping details (calls 'set_customer_info')
agents-cli run "Set my shipping info: email is shogo@example.com, address is 1600 Amphitheatre Pkwy, postal code is 94043"

# 4. Finalize payment and place order (calls 'complete_payment')
agents-cli run "Complete my payment now"
```

### 2. Run the UCP Merchant Server (Python/FastAPI)

This directory hosts the standalone **UCP Merchant Server (Python/FastAPI)** implementation.

Initialize the local mock SQLite databases with seed data:

```bash
cd rest/python/server
mkdir -p /tmp/ucp_test
uv run import_csv.py \
    --products_db_path=/tmp/ucp_test/products.db \
    --transactions_db_path=/tmp/ucp_test/transactions.db \
    --data_dir=../test_data/flower_shop
```

Start the UCP Merchant Server (Python/FastAPI) on port `8182`:

```bash
uv run server.py \
   --products_db_path=/tmp/ucp_test/products.db \
   --transactions_db_path=/tmp/ucp_test/transactions.db \
   --port=8182
```

In a separate terminal, run the validation client:

```bash
cd rest/python/client/flower_shop
uv run simple_happy_path_client.py --server_url=http://localhost:8182
```

## Commands

| Command | Description |
| :--- | :--- |
| `agents-cli install` | Install agent dependencies using uv |
| `agents-cli playground` | Launch local development playground |
| `agents-cli lint` | Run code quality checks |
| `agents-cli eval` | Evaluate agent behavior |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests |

## 🛠️ Project Management

| Command | What It Does |
| :--- | :--- |
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

To add CI/CD and Terraform, run `agents-cli scaffold enhance`.
To set up your production infrastructure, run `agents-cli infra cicd`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.
