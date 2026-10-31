FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Node.js 24 for the Vue frontend
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g npm@latest \
    && rm -rf /var/lib/apt/lists/*

# Python dev tooling
RUN pip install --no-cache-dir ruff pytest httpx

USER vscode
WORKDIR /workspace
