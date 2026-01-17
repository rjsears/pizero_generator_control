# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# GenSlave Dockerfile
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 17th, 2026
#
# Cross-compile on Mac/Linux, run on Pi Zero
# Build: docker buildx build --platform linux/arm/v6 -t rjsears/pizero_generator_control:genslave --push .
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

# Use Debian base with SYSTEM Python so apt packages work properly
# This is how Pimoroni installs their libraries on the Pi
FROM debian:bookworm-slim

LABEL maintainer="Richard J. Sears <richardjsears@protonmail.com>"
LABEL description="GenSlave - Generator relay control for Raspberry Pi Zero 2W"
LABEL version="1.0.0"

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /opt/genslave

# Install Python and all dependencies via apt (pre-compiled for ARM)
# This avoids pip trying to compile numpy/PIL from source
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    python3-numpy \
    python3-pil \
    python3-spidev \
    python3-smbus \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Note: GPIO access is provided via device mappings (/dev/gpiomem, /dev/mem)
# and the Python rpi-lgpio library installed via pip

# Create non-root user for running the app
# But we'll run as root for GPIO access (or use device mapping)
RUN useradd --create-home --shell /bin/bash genslave

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies using --break-system-packages since we're using system Python
# Use --prefer-binary to avoid compiling when possible
RUN pip install --no-cache-dir --prefer-binary --break-system-packages -r requirements.txt

# Install automationhat - numpy/PIL/spidev/smbus already installed via apt
# Tell pip to use existing packages and not reinstall numpy
RUN pip install --no-cache-dir --prefer-binary --break-system-packages \
    --no-deps st7735 \
    && pip install --no-cache-dir --prefer-binary --break-system-packages \
    RPi.GPIO \
    automationhat

# Copy application code
COPY app/ ./app/

# Create directories for data and logs
RUN mkdir -p /opt/genslave/data /opt/genslave/logs \
    && chown -R genslave:genslave /opt/genslave

# Expose the API port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import httpx; httpx.get('http://localhost:8001/health', timeout=5)" || exit 1

# Default environment variables
ENV HOST=0.0.0.0
ENV PORT=8001
ENV LOG_LEVEL=INFO
ENV FAILSAFE_TIMEOUT_SECONDS=30
ENV MOCK_HAT_MODE=false

# Run as root for GPIO access (alternatively use --device mapping)
# For production, consider using --device=/dev/gpiomem and running as genslave user

# Start the application
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
