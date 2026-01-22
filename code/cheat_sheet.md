# Cheat Sheet

This document provides a small set of commands that may be useful during the development.

## Starting a Nats Server with docker

```bash
docker run --rm -d --name nats -p 4222:4222 -p 8222:8222 nats --http_port 8222
```

## Testing Nats connection with nats-cli

```bash
nats --server nats://localhost:4222 pub test.subject "Hello, NATS!"
nats --server nats://localhost:4222 sub test.subject
```

## Docker build and running with context

```bash
docker context create show-ingest --docker "host=ssh://developer@show-ingest"  # Run once to create context

alias ds='docker --context show-ingest'  # Optional alias for convenience
ds build -t local/ai-improv-toolkit:latest . # From root of repo

ds run --rm -it --name ai-improv-toolkit-container -v /dev/show/:/dev/show/ --device=/dev/input -v /opt/show/ingest/config.toml:/etc/ai-show/config.toml local/ai-improv-toolkit
```
