# Multi-stage production container for DataSentinel CLI
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY datasentinel/ ./datasentinel/

# Build standalone distribution wheel
RUN pip install --no-cache-dir build && \
    python -m build --wheel

# Final runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /workspace

# Install system libraries for ReportLab / PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install pre-built wheel from builder stage
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

ENTRYPOINT ["datasentinel"]
CMD ["--help"]
