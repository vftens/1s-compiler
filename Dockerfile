###############################################################################
# 1S: ERP Free Edition — Docker image
# Build:   docker build -t 1s-erp .
# Run:     docker run -p 5000:5000 1s-erp
# Persist: docker run -p 5000:5000 -v ./data:/app/config 1s-erp
###############################################################################
FROM python:3.11-slim

LABEL org.opencontainers.image.title="1S: ERP Free Edition" \
      org.opencontainers.image.description="Open-source 1C-compatible ERP — bilingual RU/UK/EN" \
      org.opencontainers.image.url="https://github.com/vftens/1s-compiler" \
      org.opencontainers.image.licenses="GPL-3.0"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first (cache layer)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY src/       ./src/
COPY examples/  ./examples/

# Config dir (can be overridden by volume mount)
RUN mkdir -p config

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

ENV PYTHONUTF8=1 \
    PYTHONPATH=/app \
    FLASK_ENV=production

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/v1/ping')"

CMD ["python", "-m", "src.cli", "serve", "--host", "0.0.0.0", "--port", "5000"]
