FROM python:3.11-slim

WORKDIR /app

# Copy server files including the ucp-sdk wheel and local test_data
COPY . .

# Strip uv.sources from pyproject.toml inside the build so uv doesn't try to look for relative path beyond /app
RUN python -c "lines = open('pyproject.toml').readlines(); open('pyproject.toml', 'w').writelines(line for line in lines if not ('[tool.uv.sources]' in line or 'ucp-sdk = { path' in line or '# The relative path' in line))"

# Install uv, the prebuilt ucp-sdk wheel, and then the server package dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --system ucp_sdk-0.3.0-py3-none-any.whl && \
    uv pip install --system .

# Run db initialization on boot and start the server on port 8080 (Cloud Run port)
CMD mkdir -p /tmp/ucp_test && \
    python import_csv.py \
      --products_db_path=/tmp/ucp_test/products.db \
      --transactions_db_path=/tmp/ucp_test/transactions.db \
      --data_dir=test_data/flower_shop && \
    python server.py \
      --products_db_path=/tmp/ucp_test/products.db \
      --transactions_db_path=/tmp/ucp_test/transactions.db \
      --port=8080
