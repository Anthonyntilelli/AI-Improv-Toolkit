# Simple dev container for AI-Improv-Toolkit with Python 3.14, Ansible, Terraform, Docker CLI, openssl and make
FROM python:3.14-slim

ENV DEBIAN_FRONTEND=noninteractive

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

# Install system packages, Docker client, Ansible, Terraform (HashiCorp apt repo), openssl and make
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    lsb-release \
    unzip \
    git \
    build-essential \
    software-properties-common \
    apt-transport-https \
    docker.io \
    ansible \
    openssl \
    make \
  && rm -rf /var/lib/apt/lists/*

# Add HashiCorp apt repository and install terraform
RUN mkdir -p /etc/apt/keyrings \
  && wget -qO- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /etc/apt/keyrings/hashicorp-archive-keyring.gpg \
  && echo "deb [signed-by=/etc/apt/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends terraform \
  && rm -rf /var/lib/apt/lists/*

# Create a non-root vscode user (UID/GID passed by devcontainer build args)
RUN groupadd --gid ${USER_GID} ${USERNAME} || true \
  && useradd -m --uid ${USER_UID} --gid ${USER_GID} -s /bin/bash ${USERNAME} \
  && mkdir -p /home/${USERNAME}/.local/bin \
  && chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}

# Ensure pip is reasonably up-to-date
RUN python -m pip install --upgrade pip

# Set working dir and default user
USER ${USERNAME}
WORKDIR /home/${USERNAME}

# Ensure user local bin is on PATH for interactive sessions
ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

# Note: uv and uv-managed tools (pre-commit) are installed in post-create as the non-root user
CMD ["sleep", "infinity"]