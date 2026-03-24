FROM python:3.11-slim

WORKDIR /app

# Install system dependencies first (cached layer)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
# Auto-update yt-dlp specifically on every startup because YouTube changes frequently
CMD pip install -U yt-dlp && python main.py
