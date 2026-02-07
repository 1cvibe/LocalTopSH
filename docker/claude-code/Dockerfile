# Claude Code CLI in Docker
FROM node:22-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create workspace
WORKDIR /workspace

# Set environment variable placeholder
ENV ANTHROPIC_API_KEY=""

# Default command
CMD ["claude"]
