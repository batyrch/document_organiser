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

# Copy project files
COPY pyproject.toml .
COPY document_organizer.py .
COPY ai_providers.py .
COPY ui.py .
COPY migrate_to_jd.py .
COPY preview_renames.py .
COPY settings.py .
COPY icons.py .
COPY jd_system.py .
COPY jd_builder.py .
COPY jd_prompts.py .
COPY README.md .

# Install the package with selected providers
RUN pip install --upgrade pip && \
    pip install -e ".[${INSTALL_PROVIDERS}]"

# Create documents directory
RUN mkdir -p /documents && chown appuser:appuser /documents

# Switch to non-root user
USER appuser

# Default environment variables
ENV INBOX_DIR=/documents/inbox \
    OUTPUT_DIR=/documents/jd_documents \
    LOG_LEVEL=INFO

# Expose Streamlit port
EXPOSE 8501

# Entrypoint script
COPY --chown=appuser:appuser <<'EOF' /app/entrypoint.sh
#!/bin/bash
set -e

if [ "$1" = "ui" ]; then
    # Run Streamlit UI
    exec streamlit run ui.py --server.address=0.0.0.0 --server.port=8501
elif [ "$1" = "watch" ]; then
    # Run in watch mode
    exec python document_organizer.py "${@:2}"
elif [ "$1" = "preprocess" ]; then
    # Run preprocessing
    exec python document_organizer.py --preprocess "${@:2}"
else
    # Default: run document organizer with passed arguments
    exec python document_organizer.py "$@"
fi
EOF

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--once"]
