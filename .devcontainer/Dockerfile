FROM mcr.microsoft.com/devcontainers/python:1-3.12

# Install system packages needed for PDF export (pandoc + wkhtmltopdf)
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       pandoc \
       wkhtmltopdf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Ensure the default user is restored
USER vscode
