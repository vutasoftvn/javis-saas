# Base image with Node.js 20 on Debian
FROM node:20-bookworm-slim

WORKDIR /app

# Install curl, ca-certificates, git, and docker CLI required by Encore CLI to spin up db containers
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    build-essential \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Encore CLI
RUN curl -fsSL https://encore.dev/install.sh | bash -s -- 1.58.2
ENV PATH="/root/.encore/bin:$PATH"

# Copy package descriptors and install npm dependencies
COPY package*.json ./
RUN npm ci || npm install

# Copy application source code
COPY . .
RUN cd /app/company && (npm ci || npm install)
RUN cd /app/cosa && (npm ci || npm install)

# Ports exposed:
# 4000: Encore API Gateway (company)
# 4001: Encore API Gateway (cosa)
# 9400: Encore Local Development Dashboard & Tracing UI
EXPOSE 4000 4001 9400

# Default command: run Encore with watch mode enabled and listening on all interfaces
CMD ["encore", "run", "--listen=0.0.0.0:4000", "--browser=never"]

