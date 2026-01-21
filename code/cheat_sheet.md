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

## Docker build with context

```bash
docker context create show-ingest --docker "host=ssh://developer@show-ingest"  # Run once to create context

docker --context show-ingest build -t local/ai-improv-toolkit:latest .
docker run --rm -it --name ai-improv-toolkit-container -v /dev/show/:/dev/show/ --device=/dev/input local/ai-improv-toolkit

# To get a bash shell inside the container for debugging
docker run --rm -it --name ai-improv-toolkit-container -v /dev/show/:/dev/show/ --device=/dev/input --entrypoint /bin/bash local/ai-improv-toolkit

```
