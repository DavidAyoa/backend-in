FROM python:3.12-slim

# Build arguments
ARG BUILD_ENV=production
ARG INSTALL_DEV=false

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libssl-dev \
    pkg-config \
    libffi-dev \
    $(if [ "$BUILD_ENV" = "development" ]; then echo "vim"; fi) \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies based on build environment
RUN if [ "$BUILD_ENV" = "development" ]; then \
        uv sync --frozen --extra dev; \
    elif [ "$BUILD_ENV" = "test" ]; then \
        uv sync --frozen --extra test; \
    else \
        uv sync --frozen; \
    fi

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/logs /app/test-results

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Conditional environment variables
RUN if [ "$BUILD_ENV" = "development" ]; then \
        echo "DEVELOPMENT=true" >> /app/.env.docker; \
    elif [ "$BUILD_ENV" = "test" ]; then \
        echo "TESTING=true" >> /app/.env.docker; \
    fi

# Expose port
EXPOSE 7860

# Health check (only for production and development)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD if [ "$BUILD_ENV" != "test" ]; then curl -f http://localhost:7860/health || exit 1; fi

# Run command based on build environment
CMD if [ "$BUILD_ENV" = "development" ]; then \
        uv run python main.py --reload; \
    elif [ "$BUILD_ENV" = "test" ]; then \
        uv run pytest -v --cov=. --cov-report=html:/app/test-results/coverage --junit-xml=/app/test-results/junit.xml; \
    else \
        uv run python main.py; \
    fi
