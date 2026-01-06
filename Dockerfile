# IQ-MCP Docker Image
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies including Node.js for frontend build
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv and add to PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy scripts
COPY scripts/ ./

# Copy dependency files first (for better caching)
COPY pyproject.toml ./
COPY src/ ./src/

# Build frontend (outputs to src/mcp_knowledge_graph/web/static/)
WORKDIR /app/src/mcp_knowledge_graph/web/frontend
RUN npm install && npm run build

# Return to app root and install the package with uv
WORKDIR /app
RUN uv pip install --system -e .

# Create data directory for persistent storage
RUN mkdir -p /data /data/backups && \
    chmod 755 /data

# Environment defaults (override via docker-compose or .env)
# Note: PORT is injected by Railway/Heroku and takes precedence
ENV IQ_TRANSPORT=http \
    IQ_STREAMABLE_HTTP_HOST=0.0.0.0 \
    IQ_STREAMABLE_HTTP_PATH=/iq \
    IQ_MEMORY_PATH=/data/memory.jsonl \
    IQ_ENABLE_SUPABASE=false \
    PYTHONUNBUFFERED=1

# Run the server
CMD ["python", "-m", "mcp_knowledge_graph"]
