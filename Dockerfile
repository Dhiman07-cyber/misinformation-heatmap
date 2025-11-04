# Multi-stage Dockerfile for Real-Time Misinformation Heatmap
# Optimized for production deployment with minimal image size

# ============================================================================
# Stage 1: Base Python environment with system dependencies
# ============================================================================
FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Essential build tools
    gcc \
    g++ \
    make \
    # Network tools
    curl \
    wget \
    # For web scraping and HTML parsing
    libxml2-dev \
    libxslt1-dev \
    # For image processing (satellite data)
    libjpeg-dev \
    libpng-dev \
    # For geographic data processing
    libgeos-dev \
    libproj-dev \
    # For faster JSON processing
    libyajl-dev \
    # For Chrome/Chromium (for testing)
    chromium \
    chromium-driver \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# ============================================================================
# Stage 2: Python dependencies installation
# ============================================================================
FROM base as dependencies

# Copy requirements files
COPY backend/requirements.txt /app/requirements.txt
COPY tests/e2e/requirements.txt /app/requirements-e2e.txt

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -r requirements-e2e.txt

# Install additional production dependencies
RUN pip install \
    # Production WSGI server
    gunicorn[gthread]==21.2.0 \
    # Monitoring and logging
    prometheus-client==0.19.0 \
    structlog==23.2.0 \
    # Security
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    # Performance
    orjson==3.9.10 \
    uvloop==0.19.0 \
    # Database drivers
    asyncpg==0.29.0 \
    # Cloud integrations
    google-cloud-bigquery==3.13.0 \
    google-cloud-pubsub==2.18.4 \
    google-cloud-storage==2.10.0 \
    google-cloud-monitoring==2.16.0

# ============================================================================
# Stage 3: Application code and configuration
# ============================================================================
FROM dependencies as application

# Copy application code
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY config/ /app/config/
COPY scripts/ /app/scripts/
COPY data/ /app/data/
COPY docs/ /app/docs/

# Copy Docker-specific configurations
COPY docker/ /app/docker/

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp /app/uploads /app/cache

# Set proper permissions
RUN chown -R appuser:appuser /app && \
    chmod +x /app/scripts/*.sh && \
    chmod +x /app/scripts/*.ps1 || true

# ============================================================================
# Stage 4: Production image
# ============================================================================
FROM application as production

# Set production environment variables
ENV MODE=cloud \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    PYTHONPATH=/app/backend \
    PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Default command (can be overridden)
CMD ["python", "-m", "gunicorn", "backend.main_application:app", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--worker-connections", "1000", \
     "--max-requests", "10000", \
     "--max-requests-jitter", "1000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

# ============================================================================
# Stage 5: Development image (includes testing tools)
# ============================================================================
FROM application as development

# Install development dependencies
RUN pip install \
    # Development tools
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    pytest-html==4.1.1 \
    # Code quality
    black==23.11.0 \
    flake8==6.1.0 \
    mypy==1.7.1 \
    # Documentation
    mkdocs==1.5.3 \
    mkdocs-material==9.4.8 \
    # Debugging
    ipdb==0.13.13 \
    # Load testing
    locust==2.17.0

# Set development environment variables
ENV MODE=local \
    ENVIRONMENT=development \
    LOG_LEVEL=DEBUG \
    PYTHONPATH=/app/backend \
    PORT=8000

# Development health check (more frequent)
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=2 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Switch to non-root user
USER appuser

# Expose development port
EXPOSE 8000

# Development command with auto-reload
CMD ["python", "-m", "uvicorn", "backend.main_application:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--log-level", "debug"]