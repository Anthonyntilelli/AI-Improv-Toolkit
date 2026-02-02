# This is test Dockerfile for the AI Improv Toolkit Ingest service.
FROM python:3.14-slim

# copy uv binaries
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    build-essential \
    libopus-dev \
    libogg-dev \
    openssl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Disable development dependencies
ENV UV_NO_DEV=1

COPY pyproject.toml uv.lock /app/
RUN uv sync --locked

COPY main.py /app/
COPY common/ /app/common/
COPY ingest/ /app/ingest/

CMD ["uv", "run", "main.py"]
