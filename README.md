# Document Organizer

Automatically organize scanned documents using AI and the [Johnny.Decimal](https://johnnydecimal.com/) system.

## How It Works

```
📁 inbox/                           📁 jd_documents/
├── scan001.pdf                     ├── 10-19 Finance/
├── receipt.jpg          →          │   └── 14 Receipts/
├── contract.pdf                    │       └── 14.01 Amazon Laptop Receipt 2024.pdf
└── lab_results.pdf                 └── 20-29 Medical/
                                        └── 21 Records/
                                            └── 21.01 Charité Blood Test Results 2024.pdf
```

1. **Drop files** into the inbox folder
2. **AI extracts** text and analyzes content
3. **Files are moved** to organized folders with descriptive names

## Features

- **Privacy-First**: Documents stay local. Only extracted text goes to AI
- **Multiple AI Providers**: Claude, GPT-4, Ollama (offline), or keyword-only
- **Personalized JD System**: AI interview builds a structure for your life
- **Gallery UI**: macOS Finder-inspired interface with thumbnails
- **Duplicate Detection**: SHA256 hashing prevents filing duplicates

## Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/batyrch/document_organiser
cd document_organiser

# Run with access to your Documents folder
DOCUMENTS_PATH=$HOME/Documents docker compose up ui
```

Open http://localhost:8501 and configure paths in Settings.

#### Docker Access Options

```bash
# Mount a specific folder
DOCUMENTS_PATH=/path/to/folder docker compose up ui

# Mount entire home directory
DOCUMENTS_PATH=$HOME docker compose up ui

# Mount root filesystem (full access)
DOCUMENTS_PATH=/ docker compose up ui

# Windows (PowerShell)
$env:DOCUMENTS_PATH=$env:USERPROFILE; docker compose up ui
```

#### With .env File

Docker automatically reads from `.env` if present:

```bash
# Copy and edit .env
cp .env.example .env

# Add your API keys to .env:
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Run (reads .env automatically)
DOCUMENTS_PATH=$HOME docker compose up ui
```

Or pass keys directly:

```bash
DOCUMENTS_PATH=$HOME \
ANTHROPIC_API_KEY=sk-ant-... \
docker compose up ui
```

### Option 2: Local Python with .env

```bash
git clone https://github.com/batyrch/document_organiser
cd document_organiser

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your paths and API keys
```

Edit `.env` to set your directories:

```bash
# Required: Set your document paths
OUTPUT_DIR=~/Documents/jd_documents
INBOX_DIR=~/Documents/jd_documents/00-09 System/01 Inbox

# Optional: AI provider (auto-detects if not set)
AI_PROVIDER=auto

# Optional: API keys (if using API providers)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

Run the app:

```bash
source venv/bin/activate
streamlit run ui.py
```

### Option 3: Quick Install Script

```bash
git clone https://github.com/batyrch/document_organiser
cd document_organiser
./install.sh
docorg
```

### AI Provider Setup

| Provider | Setup |
|----------|-------|
| **Claude Code CLI** | Claude Max subscription - no API key needed |
| **Anthropic API** | `export ANTHROPIC_API_KEY="your-key"` |
| **OpenAI API** | `export OPENAI_API_KEY="your-key"` |
| **Ollama** | `ollama pull llama3.2` |

## Usage

### Web UI (Recommended)

```bash
streamlit run ui.py
```

- **Inbox Mode**: Review and classify new documents
- **Browse Mode**: Navigate existing organized files
- **Gallery View**: Thumbnails with iOS-style selection
- **Settings**: Configure directories and AI providers

### Command Line

```bash
# Preprocess only (extract + analyze, keep in inbox)
python document_organizer.py --preprocess --once

# Auto-organize (extract, analyze, and move)
python document_organizer.py --once

# Rebuild duplicate detection index
python document_organizer.py --rebuild-index
```

## Configuration

Configuration is loaded with the following priority (highest first):

1. **Settings UI** (saved in `~/Library/Application Support/DocumentOrganizer/`)
2. **Environment variables** (from `.env` or shell)
3. **config.yaml** (or `config.local.yaml` for local overrides)
4. **Defaults**

This means you can set initial paths in `.env`, then override them via the Settings UI.

### Using .env (Recommended)

```bash
cp .env.example .env
```

Key settings in `.env`:

```bash
# Document paths
OUTPUT_DIR=~/Documents/jd_documents
INBOX_DIR=~/Documents/jd_documents/00-09 System/01 Inbox

# AI provider: auto, anthropic, openai, ollama, claude-code, keywords
AI_PROVIDER=auto

# API keys (if using cloud providers)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Logging
LOG_LEVEL=INFO
```

### Using config.yaml

```yaml
paths:
  output_dir: ~/Documents/jd_documents
  inbox_dir: ~/Documents/jd_documents/00-09 System/01 Inbox
mode: claude-code  # claude-code, api, keywords
```

## Folder Structure

```
jd_documents/
├── 00-09 System/
│   ├── 00 Index/
│   └── 01 Inbox/
├── 10-19 Finance/
│   ├── 11 Banking/
│   ├── 12 Taxes/
│   └── 14 Receipts/
├── 20-29 Medical/
├── 30-39 Legal/
├── 40-49 Work/
└── 50-59 Personal/
```

Files are named: `{JD_ID} {Issuer} {DocType} {Year}.ext`

Example: `14.01 Amazon Laptop Receipt 2024.pdf`

## Supported Formats

PDF, PNG, JPG, TIFF, BMP, DOCX, PPTX, XLSX, TXT, HTML

## Requirements

- **Docker** (recommended), or
- **Python 3.10+** for local install

## Privacy

All document processing happens locally. Only extracted text is sent to AI providers. Use Ollama for 100% offline operation.

## License

MIT
