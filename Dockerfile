FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for building chromadb and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (much smaller, ~500MB vs ~2GB with CUDA)
# This reduces build time and disk space
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.0.0,<3.0.0"

# Install chromadb separately with environment variables to prevent port/temp file issues
# DuckDB (used by chromadb) may try to use port 5402, so we set env vars to prevent this
RUN mkdir -p /tmp/chromadb-install && \
    TMPDIR=/tmp/chromadb-install \
    CHROMADB_SKIP_DEPENDENCY_CHECK=1 \
    CHROMADB_SKIP_TELEMETRY=1 \
    DUCKDB_RUNTIME_DIR=/tmp/duckdb \
    pip install --no-cache-dir --timeout=300 --prefer-binary chromadb==0.5.0 || \
    (pip install --no-cache-dir --upgrade pip setuptools wheel && \
     mkdir -p /tmp/chromadb-install && \
     TMPDIR=/tmp/chromadb-install \
     CHROMADB_SKIP_DEPENDENCY_CHECK=1 \
     CHROMADB_SKIP_TELEMETRY=1 \
     DUCKDB_RUNTIME_DIR=/tmp/duckdb \
     pip install --no-cache-dir --timeout=300 --prefer-binary chromadb==0.5.0) && \
    rm -rf /tmp/chromadb-install /tmp/duckdb 2>/dev/null || true

# Use Docker-specific requirements (excluding chromadb which is already installed)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY src/ ./src/
COPY data/ ./data/

EXPOSE 8000 8501

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
