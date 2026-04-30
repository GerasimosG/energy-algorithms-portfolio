# ── Stage 1: Build (install dependencies) ────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies for HiGHS and scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ gfortran \
    libopenblas-dev liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first for layer caching
COPY pyproject.toml .

# Install Python dependencies into a wheel cache directory
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --target=/install \
    numpy>=2.0 \
    scipy>=1.12 \
    pandas>=2.0 \
    matplotlib>=3.8 \
    "pulp>=3.0" \
    "yfinance>=0.2.30" \
    pytest>=7.0 \
    pytest-cov>=4.0

# Try to install HiGHS solver (optional — won't fail the build)
RUN pip install --no-cache-dir --target=/install highspy 2>/dev/null || \
    echo "highspy not available for this platform — CBC solver will be used"

# ── Stage 2: Runtime (minimal image) ─────────────────────────────────
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="Energy Algorithms"
LABEL org.opencontainers.image.description="Optimization portfolio: energy markets (PCR/Euphemia), LP/MIP, backtesting"
LABEL org.opencontainers.image.source="https://github.com/GerasimosG/Energy_Algorithms"

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local/lib/python3.13/site-packages/

# Set workdir and copy source code
WORKDIR /app
COPY . .

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -q energy_markets/ energy_data/ lp_optimization/ backtester/ strategies/ market_data/ 2>/dev/null || true

# Default command: run tests
CMD ["pytest", "tests/", "-v", "--tb=short"]
