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
    && apt-get install -y --no-install-recommends terraform whois \
    && rm -rf /var/lib/apt/lists/*

# Install system packages used by the application
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    libasound2-dev \
    build-essential \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Install Starship prompt
RUN wget -qO- https://starship.rs/install.sh | sh -s -- -y
