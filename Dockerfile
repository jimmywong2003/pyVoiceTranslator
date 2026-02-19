# VoiceTranslate Pro - Production Docker Image
# Multi-stage build for optimized production deployment

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
COPY requirements-prod.txt .

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-prod.txt

# =============================================================================
# Stage 2: Production
# =============================================================================
FROM python:3.11-slim as production

LABEL maintainer="VoiceTranslate Team"
LABEL version="1.0.0"
LABEL description="Real-time voice translation with streaming optimization"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VOICETRANSLATE_ENV=production \
    VOICETRANSLATE_LOG_LEVEL=INFO \
    VOICETRANSLATE_ENABLE_METRICS=true

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libportaudio2 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create non-root user for security
RUN groupadd -r voicetranslate && \
    useradd -r -g voicetranslate -s /bin/false voicetranslate && \
    mkdir -p /app/data /app/logs && \
    chown -R voicetranslate:voicetranslate /app

# Switch to non-root user
USER voicetranslate

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Expose port for health endpoint
EXPOSE 8080

# Default entrypoint
ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--mode", "streaming"]

# =============================================================================
# Stage 3: Development
# =============================================================================
FROM production as development

USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Install test dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

USER voicetranslate

ENV VOICETRANSLATE_ENV=development
ENV PYTHONDEVMODE=1
