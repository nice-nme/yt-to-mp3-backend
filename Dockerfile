FROM python:3.10-slim

# Install system dependencies (ffmpeg is required for audio extraction)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements list first
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (Render sets PORT environment variable, defaults to 5000 or as defined)
EXPOSE 5000

# Start app using gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --timeout 180 --workers 2 app:app"]
