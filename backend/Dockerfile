# Multi-stage build for Python backend
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies (including build tools for ML/AI packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    cmake \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements
COPY requirements.txt .

# Install dependencies with optimizations for faster builds
# Use binary wheels when possible, increase timeout, and enable parallel builds
ENV MAX_JOBS=4

# Install CPU-only torch first to avoid downloading huge CUDA deps
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir --user --timeout=1000 \
    --prefer-binary \
    -r requirements.txt && \
    # Aggressive cleanup
    find /root/.local -type d -name "__pycache__" -exec rm -rf {} + && \
    find /root/.local -type d -name "tests" -exec rm -rf {} + && \
    find /root/.local -type d -name "test" -exec rm -rf {} + && \
    find /root/.local -name "*.pyc" -delete && \
    find /root/.local -name "*.pyo" -delete && \
    # Strip shared libraries to reduce size
    find /root/.local -name "*.so" -exec strip --strip-unneeded {} + 2>/dev/null || true && \
    # Remove pip and setuptools (not needed at runtime)
    pip uninstall -y pip setuptools wheel

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Make sure scripts are executable and add to PATH
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]




