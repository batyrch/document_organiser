# Document Organizer - Docker Image
#
# Build:
#   docker build -t document-organizer .
#
# Run (processing mode):
#   docker run -v /path/to/documents:/documents \
#     -e ANTHROPIC_API_KEY=your_key \
#     document-organizer --once
#
# Run (Streamlit UI):
#   docker run -p 8501:8501 -v /path/to/documents:/documents \
#     -e ANTHROPIC_API_KEY=your_key \
#     document-organizer ui

FROM python:3.11-slim

# Build arguments
ARG INSTALL_PROVIDERS=anthropic,openai

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# Note: libgl1 replaces libgl1-mesa-glx in newer Debian (trixie+)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy project files and set ownership to appuser
COPY --chown=appuser:appuser pyproject.toml .
COPY --chown=appuser:appuser document_organizer.py .
COPY --chown=appuser:appuser ai_providers.py .
COPY --chown=appuser:appuser ui.py .
COPY --chown=appuser:appuser migrate_to_jd.py .
COPY --chown=appuser:appuser preview_renames.py .
COPY --chown=appuser:appuser settings.py .
COPY --chown=appuser:appuser icons.py .
COPY --chown=appuser:appuser jd_system.py .
COPY --chown=appuser:appuser jd_builder.py .
COPY --chown=appuser:appuser jd_prompts.py .
COPY --chown=appuser:appuser README.md .

# Install the package with selected providers
RUN pip install --upgrade pip && \
    pip install -e ".[${INSTALL_PROVIDERS}]"

# Create documents directory and config directory for settings
RUN mkdir -p /documents && chown appuser:appuser /documents && \
    mkdir -p /home/appuser/.config/DocumentOrganizer && \
    chown -R appuser:appuser /home/appuser/.config

# Create entrypoint script (POSIX-compatible, before switching to non-root user)
RUN printf '%s\n' \
    '#!/bin/sh' \
    'set -e' \
    '' \
    'case "$1" in' \
    '    ui)' \
    '        exec streamlit run ui.py --server.address=0.0.0.0 --server.port=8501' \
    '        ;;' \
    '    watch)' \
    '        shift' \
    '        exec python document_organizer.py "$@"' \
    '        ;;' \
    '    preprocess)' \
    '        shift' \
    '        exec python document_organizer.py --preprocess "$@"' \
    '        ;;' \
    '    *)' \
    '        exec python document_organizer.py "$@"' \
    '        ;;' \
    'esac' \
    > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

# Default environment variables
ENV INBOX_DIR=/documents/inbox \
    OUTPUT_DIR=/documents/jd_documents \
    LOG_LEVEL=INFO

# Expose Streamlit port
EXPOSE 8501

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--once"]
