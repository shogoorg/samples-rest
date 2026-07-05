# samples-rest

This Project enables running the UCP Merchant Server using agents-cli.

agents-cli <https://github.com/Universal-Commerce-Protocol/samples/tree/main/rest/python/server> is a CLI and skill for building agents on the Gemini Enterprise Agent Platform.

The UCP Merchant Server (Python/FastAPI) <https://github.com/Universal-Commerce-Protocol/samples/tree/main/rest/python/server> is a reference implementation of the UCP Merchant Server designed to be deployed both inside and outside of Google. 

This repository is a cloned and reused version of the UCP Merchant Server, which has been refactored to support interactive shopping flows and agent verification using `agents-cli`.

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

This agent simulates a full customer shopping checkout flow referencing the **UCP (Universal Commerce Protocol)** and its sample REST implementation.

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

> ⚠️ **Important:** Before starting the playground or running the agent commands, you must first run the UCP Merchant Server. Please follow the instructions in [2. Run the UCP Merchant Server (Python/FastAPI)](#2-run-the-ucp-merchant-server-pythonfastapi) below to start the server.

Or test the agent directly from your terminal using commands to run through the entire shopping flow:

> ⚠️ **Note:** To maintain the checkout state across sequential terminal runs, you must append the `--session-id <session_id>` flag (using the ID printed in the console from the previous run) to each subsequent command. Alternatively, use `agents-cli playground` to handle session states automatically.

```bash
# 1. Discover payment methods (calls 'discover_payment_methods')
agents-cli run "What payment methods are supported?"

# 2. Start a checkout session (calls 'create_checkout_session')
agents-cli run "Create a checkout session with bouquet_roses for John Doe, email john.doe@example.com"

# 3. Add more items to the checkout (calls 'add_item_to_checkout')
agents-cli run "Add two pot_ceramic to my checkout" --session-id  0070f53b-5956-44e6-916c-52dab2346b6a　<session_id>

# 4. Apply a discount code (calls 'apply_discount_code')
agents-cli run "Apply discount code 10OFF" --session-id  0070f53b-5956-44e6-916c-52dab2346b6a　<session_id>

# 5. Set shipping address (calls 'select_fulfillment_destination')
agents-cli run "My shipping address is 1600 Amphitheatre Pkwy, postal code is 94043" --session-id  0070f53b-5956-44e6-916c-52dab2346b6a　<session_id>

# 6. Select shipping option (calls 'select_fulfillment_option')
agents-cli run "Select the standard shipping option" --session-id  0070f53b-5956-44e6-916c-52dab2346b6a　<session_id>

# 7. Finalize payment and place order (calls 'complete_payment')
agents-cli run "Complete my payment using mock_payment_handler" --session-id  0070f53b-5956-44e6-916c-52dab2346b6a<session_id>
```

Example commands in Japanese (to run the entire shopping flow using Japanese prompts):

> ⚠️ **Note:** To maintain the checkout state across sequential terminal runs, you must append the `--session-id <session_id>` flag (using the ID printed in the console from the previous run) to each subsequent command. Alternatively, use `agents-cli playground` to handle session states automatically.

```bash
# 1. サポートされている決済方法を確認する
agents-cli run "サポートされている決済方法は何ですか？"

# 2. チェックアウトセッションを開始する
agents-cli run "John Doe（メールアドレス john.doe@example.com）のために、bouquet_roses でチェックアウトセッションを作成してください"

# 3. チェックアウトに商品を追加する（pot_ceramic を2つ追加）
agents-cli run "チェックアウトに pot_ceramic を2つ追加してください" --session-id <session_id>

# 4. 割引コードを適用する（コード: 10OFF）
agents-cli run "割引コード 10OFF を適用してください" --session-id <session_id>

# 5. 配送先住所を設定する
agents-cli run "配送先住所は 1600 Amphitheatre Pkwy、郵便番号は 94043 です" --session-id <session_id>

# 6. 配送方法を選択する（標準配送を選択）
agents-cli run "標準配送オプションを選択してください" --session-id <session_id>

# 7. 決済を完了し注文を確定する（mock_payment_handler を使用）
agents-cli run "mock_payment_handler を使用して決済を完了してください" --session-id <session_id>
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

### Cloud Run Deployment
If deploying the merchant server on Google Cloud:
- **Server URL**: `https://<YOUR_UCP_SERVER_URL>`
- **Discovery URL**: `https://<YOUR_UCP_SERVER_URL>/.well-known/ucp`

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

## Deployment

Deploy the ADK Agent to Cloud Run and expose it publicly:

```bash
# 1. Deploy with your UCP Merchant Server URL
agents-cli deploy --update-env-vars="UCP_SERVER_URL=https://<YOUR_UCP_SERVER_URL>" --project=<YOUR_PROJECT_ID> --no-confirm-project

# 2. Expose the service to allow public access
gcloud run services add-iam-policy-binding samples-rest \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=us-east1 \
  --project=<YOUR_PROJECT_ID>
```


## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.
