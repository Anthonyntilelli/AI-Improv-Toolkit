# Cheat Sheet

This document provides a small set of command that may be useful during the development.

## Starting a Nats Server with docker

```bash
docker run --rm --name nats  --rm -p 4222:4222 -p 8222:8222 nats --http_port 8222
```

## Testing Nats connection with nats-cli

```bash
nats --server nats://localhost:4222 pub test.subject "Hello, NATS!"
nats --server nats://localhost:4222 sub test.subject
```
