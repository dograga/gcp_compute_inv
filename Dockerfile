# Use an official Python runtime as a parent image
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Create a non-root user with a valid home directory
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --home /home/appuser appuser

# Set HOME and cache directory for uv
ENV HOME=/home/appuser
ENV XDG_CACHE_HOME=/tmp/uv_cache
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Copy source code
COPY . .

# Set proper permissions for everything
RUN mkdir -p /app/creds && \
    chmod -R 755 /app/creds && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Set entrypoint
ENTRYPOINT ["uv", "run", "python", "entrypoint.py"]
