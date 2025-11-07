FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt ./

# Install Python dependencies (this layer will be cached if requirements.txt doesn't change)
# Install torch from PyTorch index, then other packages from PyPI
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch && \
    pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt


# Copy application code (this layer changes more frequently)
COPY mcp_app/ ./mcp_app/
COPY data/ ./data/
COPY .env ./.env

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=http://host.docker.internal:11434

# Run the MCP server
CMD ["python", "-m", "mcp_app.main"]
