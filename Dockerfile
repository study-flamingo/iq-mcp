# IQ-MCP Docker Image
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for better caching)
COPY pyproject.toml ./
COPY src/ ./src/

# Install the package (supabase is now in main deps)
RUN pip install --no-cache-dir -e .

# Create data directory for persistent storage
RUN mkdir -p /data /data/backups && \
    chmod 755 /data

# Environment defaults (override via docker-compose or .env)
ENV IQ_TRANSPORT=http \
    IQ_STREAMABLE_HTTP_HOST=0.0.0.0 \
    IQ_STREAMABLE_HTTP_PORT=8000 \
    IQ_STREAMABLE_HTTP_PATH=/mcp \
    IQ_MEMORY_PATH=/data/memory.jsonl \
    IQ_ENABLE_SUPABASE=true \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Run the server
CMD ["python", "-m", "mcp_knowledge_graph"]
