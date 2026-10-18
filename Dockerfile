###############################################################################
# 1S: ERP Free Edition — Docker image
# Build:   docker build -t 1s-erp .
# Run:     docker run -p 5000:5000 1s-erp
# Persist: docker run -p 5000:5000 -v ./data:/app/config 1s-erp
###############################################################################
# ── Stage 1: GridCraft spreadsheet engine (Rust) ─────────────────────────────
# Reads .xls/.xlsx/.ods, writes .xlsx for the trial balance reconciliation demo
# (/demo/sverka). ~15 MB binary. Compiling needs ~2 GB RAM: on a 1 GB VPS build
# the image elsewhere (GitHub Actions -> ghcr.io) and `docker pull` it, see
# docs/site-demo.md. Build without it: --build-arg GRIDCRAFT_REF=none
ARG GRIDCRAFT_REF=v0.8.0
FROM rust:1.90-slim-bookworm AS gridcraft
ARG GRIDCRAFT_REF
ENV CARGO_BUILD_JOBS=2 CARGO_PROFILE_RELEASE_LTO=thin
RUN mkdir -p /out/bin && if [ "$GRIDCRAFT_REF" != "none" ]; then \
      apt-get update && apt-get install -y --no-install-recommends git pkg-config ca-certificates \
      && cargo install --git https://github.com/storytold/gridcraft --tag "$GRIDCRAFT_REF" \
           --locked --root /out gridcraft-cli \
      && rm -rf /usr/local/cargo/registry /usr/local/cargo/git; \
    fi

# ── Stage 2: 1S ──────────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm

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

# GridCraft binary (empty dir when built with GRIDCRAFT_REF=none) + its licence
COPY --from=gridcraft /out/bin/ ./bin/
COPY third_party/ ./third_party/

# Config dir (can be overridden by volume mount)
RUN mkdir -p config

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

ENV PYTHONUTF8=1 \
    PYTHONPATH=/app \
    GRIDCRAFT_CLI=/app/bin/gridcraft-cli \
    FLASK_ENV=production

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/v1/ping')"

CMD ["python", "-m", "src.cli", "serve", "--host", "0.0.0.0", "--port", "5000"]
