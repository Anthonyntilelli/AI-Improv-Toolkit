# This is test Dockerfile for the AI Improv Toolkit Ingest service.
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system packages used by the application
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    libasound2-dev \
    build-essential \
    openssl \
    libusb-1.0-0-dev \
    libudev-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

# Disable development dependencies
ENV UV_NO_DEV=1

WORKDIR /app
RUN uv sync --locked

CMD ["uv", "run", "main.py"]
