# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY source/ ./source/
COPY resources/ ./resources/

# Create persistent cache directories that will be mounted as volumes
RUN mkdir -p /app/data/embeddings_cache \
    /app/data/category_queries \
    /app/data/persistence

# Set Python path to include the app directory
ENV PYTHONPATH=/app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose ports (8000 for main app, 8080 for LiveKit server)
EXPOSE 8000 8080

# Default command - run the main web application
CMD ["python", "source/web_app/app.py"]