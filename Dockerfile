# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run expects the container to listen on PORT
# But our bot is a cron job, so we'll just run the script
ENV PORT=8080

# Run the GCP cron script when container starts
CMD ["python", "run_cron_gcp.py"]
