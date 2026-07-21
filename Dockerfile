FROM python:3.12-slim

# System dependencies for WeasyPrint + mysqlclient + Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libmariadb-dev \
    libxml2-dev \
    libxslt1-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-dejavu \
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Ensure entrypoint is executable
RUN chmod +x docker/entrypoint.sh

# Create non-root user + ensure volume mount points are writable
RUN useradd -m -u 1000 visota \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R visota:visota /app
USER visota

EXPOSE 8900

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8900/health/ || exit 1

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn config.asgi:application --host 0.0.0.0 --port 8900 --workers ${UVICORN_WORKERS:-4} --timeout-keep-alive 5 --log-level info --access-log"]
