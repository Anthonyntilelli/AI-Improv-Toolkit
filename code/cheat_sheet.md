# Cheat Sheet

This document provides a small set of commands that may be useful during the development.

## Started docker containers for the show (testing only no)

```bash
docker run --rm -d --name nats -p 4222:4222 -p 8222:8222 nats --http_port 8222
docker run --rm -it --name ingest -v /dev/show/:/dev/show/ --device=/dev/input -v /opt/show/ingest/config.toml:/etc/ai-show/config.toml local/ai-improv-toolkit
```

## Testing Nats connection with nats-cli

```bash
nats --server nats://localhost:4222 pub test.subject "Hello, NATS!"
nats --server nats://localhost:4222 sub test.subject
```
