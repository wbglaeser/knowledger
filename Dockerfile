# Use Python 3.14 base image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock* ./

# Install dependencies first (for better layer caching)
RUN uv sync

# Copy application code
COPY src/ ./src/
COPY templates/ ./templates/

# Create directories for database, static files, and lib
RUN mkdir -p /data /app/static /app/lib

# Set Python path
ENV PYTHONPATH=/app

# Expose web UI port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uv", "run", "python", "src/main.py"]
