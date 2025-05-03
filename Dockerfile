# Use an official Python runtime as a parent image
FROM python:3.10-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Create a non-root user and switch to it
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Copy source code
COPY . .

# Create the /app/creds directory and set correct permissions
RUN mkdir -p /app/creds && chmod -R 755 /app/creds && chown -R appuser:appgroup /app/creds

# Change ownership of the app directory
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Set a valid cache directory for uv
ENV XDG_CACHE_HOME=/tmp/uv_cache

# Run the script
CMD uv run python gke/main.py
