FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Whisper (ffmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# NOTE: Model will be downloaded at runtime (first run only)
# This avoids out-of-memory issues during Docker build
# Model is cached after first download

# Copy application code
COPY app/ ./app/

# Create logs directory
RUN mkdir -p /app/logs

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default command (can be overridden in docker-compose)
CMD ["python", "-u", "-m", "app.main", "--mode", "once"]
