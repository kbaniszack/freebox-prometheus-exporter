FROM python:3.11-slim

WORKDIR /app

# Install compilation tools for freepybox pip install
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies with build bypass
RUN pip install --no-cache-dir requests setuptools wheel && \
    pip install --no-cache-dir --no-build-isolation freepybox prometheus-client

# Copy application code
COPY freebox_exporter.py .

# Environment variables
ENV FREEBOX_EXPORTER_PORT=8000
ENV FREEBOX_POLLING_INTERVAL=10
ENV FREEBOX_IP="192.168.1.254"
ENV FREEBOX_TOKEN_PATH="/app/freebox_token.json"

EXPOSE 8000

CMD ["python", "freebox_exporter.py"]
