FROM mcr.microsoft.com/devcontainers/python:2-3.14-trixie

# Install Terraform and whois
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gpg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && wget -qO- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /etc/apt/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    terraform \
    whois \
    docker-cli \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install system packages used by the application
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    libasound2-dev \
    build-essential \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Switch to vscode user for uv and tools installation
USER vscode

# Install uv (Python package manager) as vscode user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Pre-install tools with uv
RUN /home/vscode/.local/bin/uv tool install pre-commit && \
    /home/vscode/.local/bin/uv tool install ansible-core --with ansible && \
    /home/vscode/.local/bin/uv tool install ansible-lint && \
    /home/vscode/.local/bin/uv cache clean
