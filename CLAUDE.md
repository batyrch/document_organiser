# Document Organizer - Claude Code Guide

## Overview

AI-powered document organizer using the Johnny.Decimal system. Extracts text from PDFs/images, categorizes with AI, and files documents into a structured folder hierarchy.

The project has two frontends:
1. **Streamlit UI** (`ui.py`) - Current web-based interface
2. **Electron App** (`document-organizer-electron/`) - Native macOS desktop app (in development)

Both frontends share the same Python backend for document processing.

## Project Structure

```
document_organiser/
├── # ===== PYTHON BACKEND (shared) =====
├── document_organizer.py   # Core organizer: text extraction, AI categorization, file organization
├── ai_providers.py         # Pluggable AI providers (Claude, OpenAI, Ollama, Bedrock)
├── settings.py             # Persistent settings with keychain storage for API keys
├── jd_system.py            # Dynamic JD system management (jdex.json)
├── jd_builder.py           # AI-powered JD system builders (Interview, Wizard)
├── jd_prompts.py           # AI prompts for JD system generation
├── api_server.py           # JSON-RPC API for Electron IPC (stdin/stdout)
│
├── # ===== STREAMLIT FRONTEND =====
├── ui.py                   # Streamlit web UI with gallery view
├── icons.py                # Lucide SVG icons for Streamlit UI
│
├── # ===== ELECTRON FRONTEND =====
├── document-organizer-electron/
│   ├── src/
│   │   ├── main/                    # Electron main process
│   │   │   ├── index.ts             # Window management, app lifecycle
│   │   │   ├── python-bridge.ts     # Spawn Python backend, JSON IPC
│   │   │   ├── ipc-handlers.ts      # IPC handlers for renderer
│   │   │   ├── thumbnails.ts        # Thumbnail generation with sharp
│   │   │   └── menu.ts              # Native app menu
│   │   ├── renderer/                # React frontend
│   │   │   ├── App.tsx              # Main app with router
│   │   │   ├── pages/
│   │   │   │   ├── DocumentsPage.tsx
│   │   │   │   ├── SettingsPage.tsx
│   │   │   │   └── SetupWizard.tsx
│   │   │   ├── components/
│   │   │   │   ├── Gallery/
│   │   │   │   │   ├── GalleryStrip.tsx      # 7-thumbnail horizontal gallery
│   │   │   │   │   └── ThumbnailCard.tsx     # Individual thumbnail with selection
│   │   │   │   ├── Preview/
│   │   │   │   │   ├── DocumentPreview.tsx   # Tabbed preview container
│   │   │   │   │   ├── PDFViewer.tsx         # PDF rendering with pdfjs-dist
│   │   │   │   │   └── ImageViewer.tsx
│   │   │   │   ├── Actions/
│   │   │   │   │   └── Toolbar.tsx           # Move/Analyze/Delete actions
│   │   │   │   ├── Sidebar/
│   │   │   │   │   └── Sidebar.tsx           # Navigation, stats, file source
│   │   │   │   ├── Settings/
│   │   │   │   │   ├── DirectoriesTab.tsx
│   │   │   │   │   ├── AIProviderTab.tsx
│   │   │   │   │   └── JDSystemTab.tsx
│   │   │   │   ├── JDBuilder/
│   │   │   │   │   └── InterviewChat.tsx     # AI chat for JD system creation
│   │   │   │   └── common/
│   │   │   │       ├── TagChips.tsx
│   │   │   │       ├── Breadcrumb.tsx
│   │   │   │       └── HandSpinner.tsx
│   │   │   ├── store/
│   │   │   │   └── useAppStore.ts    # Zustand state management
│   │   │   ├── hooks/
│   │   │   │   ├── useThumbnail.ts
│   │   │   │   └── useFileOperations.ts
│   │   │   └── styles/
│   │   │       ├── globals.css
│   │   │       └── animations.css
│   │   └── shared/
│   │       └── types.ts              # Shared TypeScript types
│   ├── package.json
│   └── forge.config.ts              # Electron Forge build config
│
├── # ===== CONFIGURATION =====
├── config.yaml             # Configuration (paths, AI model, logging)
├── .env.example            # Environment variables template
├── .env                    # Local environment config (not in git)
├── requirements.txt        # Python dependencies
├── install.sh              # macOS/Linux installer
├── Dockerfile              # Container build
└── docker-compose.yml      # Docker orchestration
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTENDS                                │
├────────────────────────────┬────────────────────────────────────┤
│      Streamlit UI          │         Electron App               │
│      (ui.py)               │    (document-organizer-electron)   │
│                            │                                    │
│  - Browser-based           │  - Native macOS app                │
│  - Hot reload              │  - React + TypeScript              │
│  - Docker support          │  - Zustand state management        │
│                            │  - pdfjs-dist for PDF preview      │
└────────────┬───────────────┴──────────────────┬─────────────────┘
             │ Direct Python imports            │ JSON IPC (stdin/stdout)
             │                                  │
             ▼                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PYTHON BACKEND                              │
├─────────────────────────────────────────────────────────────────┤
│  api_server.py (for Electron)                                   │
│    - Reads JSON commands from stdin                             │
│    - Routes to appropriate module                               │
│    - Returns JSON responses to stdout                           │
├─────────────────────────────────────────────────────────────────┤
│  document_organizer.py        │  ai_providers.py                │
│    - extract_text_*()         │    - AnthropicProvider          │
│    - categorize_with_*()      │    - OpenAIProvider             │
│    - organize_file()          │    - OllamaProvider             │
│    - build_hash_index()       │    - ClaudeCodeProvider         │
├───────────────────────────────┼─────────────────────────────────┤
│  jd_system.py                 │  settings.py                    │
│    - JDSystem class           │    - Settings class             │
│    - JDValidator              │    - Keychain storage           │
│    - jdex.json management     │    - .env loading               │
├───────────────────────────────┴─────────────────────────────────┤
│  jd_builder.py                                                  │
│    - InterviewBuilder (AI chat for JD creation)                 │
│    - WizardBuilder (template-based)                             │
└─────────────────────────────────────────────────────────────────┘
```

## Electron IPC Protocol

The Electron app communicates with Python via JSON-RPC over stdin/stdout.

**Request format:**
```json
{
  "id": "uuid-v4",
  "method": "files:list",
  "params": {
    "folder": "/path/to/folder",
    "recursive": true
  }
}
```

**Response format:**
```json
{
  "id": "uuid-v4",
  "result": { ... },
  "error": null
}
```

**Available methods:**
| Method | Description | Params |
|--------|-------------|--------|
| `files:list` | List files in folder | `folder`, `recursive` |
| `files:analyze` | Extract text + AI categorize | `filePath` |
| `files:move` | Organize to JD location | `filePath`, `area`, `category` |
| `files:delete` | Delete file + metadata | `filePath` |
| `settings:get` | Get all settings | - |
| `settings:set` | Update settings | `key`, `value` |
| `jd:getAreas` | Get JD structure | - |
| `jd:startInterview` | Start JD builder chat | - |
| `jd:sendMessage` | Send chat message | `message` |
| `jd:acceptProposal` | Accept JD structure | - |
| `thumbnails:generate` | Generate thumbnail | `filePath` |

## Electron Component Mapping

Mapping from Streamlit UI (ui.py) to Electron React components:

| Streamlit Function | React Component | Notes |
|--------------------|-----------------|-------|
| `render_gallery_strip()` | `GalleryStrip.tsx` | 7 visible thumbnails, pagination |
| `render_preview()` | `DocumentPreview.tsx` | Tabs: Preview + Extracted Text |
| `render_classification()` | `ClassificationPanel.tsx` | Metadata display + tags |
| `render_actions_toolbar()` | `Toolbar.tsx` | Area/Category dropdowns + buttons |
| `render_settings_page()` | `SettingsPage.tsx` | 4 tabs: Dirs, AI, JD, About |
| `render_jd_interview()` | `InterviewChat.tsx` | Chat UI for JD builder |
| `render_setup_wizard()` | `SetupWizard.tsx` | First-run configuration |
| `render_breadcrumb()` | `Breadcrumb.tsx` | Clickable path navigation |
| `render_tag_chips()` | `TagChips.tsx` | Colored tag display |
| `show_hand_loading()` | `HandSpinner.tsx` | Animated loading indicator |
| `generate_thumbnail()` | `thumbnails.ts` (main) | Uses sharp + pdfjs-dist |

## State Management (Electron)

Zustand store structure (`useAppStore.ts`):

```typescript
interface AppState {
  // Navigation
  currentPage: 'documents' | 'settings';
  browseMode: boolean;
  browseFolderPath: string;
  browseRecursive: boolean;
  navHistory: string[];
  navHistoryIdx: number;

  // Files
  files: FileEntry[];
  currentFileIdx: number;
  selectionMode: boolean;
  selectedFiles: Set<string>;
  searchQuery: string;
  searchField: string;

  // Session
  processedCount: number;
  setupComplete: boolean;

  // Actions
  loadFiles: (folder: string, recursive: boolean) => Promise<void>;
  analyzeFile: (path: string) => Promise<void>;
  moveFile: (path: string, area: string, category: string) => Promise<void>;
  deleteFile: (path: string) => Promise<void>;
}
```

## Core Modules

### document_organizer.py
Main processing engine.

**Key Functions:**
- `extract_text_with_docling()` / `extract_text_fallback()` - Text extraction from documents
- `categorize_with_claude_code()` / `categorize_with_llm()` / `categorize_with_keywords()` - AI categorization
- `organize_file()` - Move file to JD folder structure with metadata
- `preprocess_file()` / `preprocess_inbox()` - Extract + analyze without moving
- `get_merged_jd_areas()` - Merge hardcoded JD_AREAS with filesystem folders and jdex.json
- `scan_jd_folders()` - Discover user folders (includes empty areas for new categories)
- `build_hash_index()` / `find_duplicate_in_index()` - SHA256-based duplicate detection

**CLI:**
```bash
python document_organizer.py --preprocess --once  # Analyze inbox files
python document_organizer.py --once               # Auto-organize files
python document_organizer.py --rebuild-index      # Rebuild hash index
```

### ai_providers.py
Pluggable AI backend system.

**Providers:**
- `AnthropicProvider` - Claude API (has `chat()`)
- `OpenAIProvider` - GPT API (has `chat()`)
- `ClaudeCodeProvider` - Claude Code CLI (Max subscription)
- `BedrockProvider` - AWS Bedrock
- `OllamaProvider` - Local Ollama
- `KeywordProvider` - Keyword matching (no AI)

**Key Functions:**
- `get_provider(name)` - Get provider by name or auto-detect
- `get_chat_provider()` - Get provider that supports multi-turn chat
- `categorize_document()` - Categorize with automatic fallback

### settings.py
Platform-specific settings with secure keychain storage. Loads `.env` automatically.

**Configuration Priority** (highest first):
1. Saved settings from UI (JSON file)
2. Environment variables (from `.env` or shell)
3. Defaults

This allows users to set initial paths in `.env`, then override via Settings UI.

**Storage Locations:**
- macOS: `~/Library/Application Support/DocumentOrganizer/settings.json`
- Linux: `~/.config/DocumentOrganizer/settings.json`
- API keys: OS keychain (not in JSON)

**Key Properties:**
- `Settings.output_dir` - Resolves: saved setting > OUTPUT_DIR env var > default
- `Settings.inbox_dir` - Resolves: saved setting > INBOX_DIR env var > default
- `Settings.get_effective_provider()` - Auto-detect best AI provider

**Key Functions:**
- `get_settings()` - Global Settings instance
- `Settings.get()` / `Settings.set()` - Read/write settings

### jd_system.py
Dynamic JD structure management.

**Classes:**
- `JDValidator` - Enforces JD constraints (max 10 areas, max 10 categories per area)
- `JDSystem` - Load/save jdex.json, create folders, track statistics

**Storage:** `{output_dir}/00-09 System/00 Index/jdex.json`

### jd_builder.py
AI-powered JD system creation.

**Classes:**
- `InterviewBuilder` - Conversational system design via AI chat
- `WizardBuilder` - Template-based setup (personal, freelance, employee)
- `DocumentAnalysisBuilder` - Learn from existing documents (placeholder)

### ui.py
Streamlit web interface.

**Features:**
- Gallery view with thumbnails (macOS Finder-inspired)
- iOS-style selection mode (Select/Done toggle)
- Browse mode for navigating existing files
- Settings page with AI provider configuration
- JD System builder with interview chat interface
- Toolbar auto-syncs Area/Category with AI suggestions on file change

**Key Components:**
- `render_gallery_strip()` - Paginated thumbnail gallery
- `render_preview()` - Full-width document preview
- `render_classification()` - AI analysis display
- `render_actions_toolbar()` - Move/Reanalyze/Delete actions (syncs with AI suggestions)
- `render_settings_page()` - Settings UI with tabs
- `render_jd_interview()` - Chat interface for JD builder

**Toolbar Sync Logic:**
When user selects a different file, the toolbar clears cached selections (`toolbar_area`, `toolbar_category`) so dropdowns re-initialize with the new file's AI-suggested Area/Category.

## Johnny.Decimal System

Documents organized as: `Area/Category/{JD_ID} {Issuer} {DocType} {Year}.ext`

Example: `10-19 Finance/14 Receipts/14.01 Amazon Laptop Receipt 2024.pdf`

**Default Areas:**
- 00-09 System (Index, Inbox, Uncategorized)
- 10-19 Finance (Banking, Taxes, Insurance, Receipts)
- 20-29 Medical (Records, Insurance, Prescriptions)
- 30-39 Legal (Contracts, Property, Identity)
- 40-49 Work (Employment, Expenses, Salary)
- 50-59 Personal (Education, Travel, Certificates)

**ID Assignment:** Same issuer + same year = same JD ID

## Configuration

### .env (Recommended)
```bash
# Document paths
OUTPUT_DIR=~/Documents/jd_documents
INBOX_DIR=~/Documents/jd_documents/00-09 System/01 Inbox

# AI provider: auto, anthropic, openai, ollama, claude-code, keywords
AI_PROVIDER=auto

# API keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Logging
LOG_LEVEL=INFO
```

### config.yaml
```yaml
paths:
  output_dir: ~/Documents/jd_documents
  inbox_dir: ~/Documents/jd_documents/00-09 System/01 Inbox
mode: claude-code  # claude-code, api, keywords
ai:
  model: claude-sonnet-4-20250514
```

## Metadata

Each document gets a `.meta.json` sidecar:
```json
{
  "id": "14.01",
  "jd_area": "10-19 Finance",
  "jd_category": "14 Receipts",
  "issuer": "Amazon",
  "document_type": "Laptop Receipt",
  "document_date": "2024-12-20",
  "tags": ["receipt", "electronics"],
  "summary": "...",
  "extracted_text": "..."
}
```

## Running

### Option 1: Docker
```bash
# With .env file (recommended)
cp .env.example .env  # Edit with your settings
DOCUMENTS_PATH=$HOME docker compose up ui

# Open http://localhost:8501
```

### Option 2: Local Python with .env
```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings

# Run
streamlit run ui.py
```

### Option 3: Install Script
```bash
./install.sh
docorg
```

### CLI Commands
```bash
# Preprocess inbox (extract + analyze, keep in inbox)
python document_organizer.py --preprocess --once

# Auto-organize (extract, analyze, and move)
python document_organizer.py --once

# Rebuild duplicate detection index
python document_organizer.py --rebuild-index
```

### Option 4: Electron App (macOS)
```bash
cd document-organizer-electron

# Development
npm install
npm start

# Build for distribution
npm run make
# Output: out/make/Document Organizer.dmg
```

## Development Workflow

### Working on Streamlit UI
```bash
streamlit run ui.py
# Edit ui.py, changes hot-reload
```

### Working on Electron App
```bash
cd document-organizer-electron
npm start
# Edit React components, Vite hot-reloads renderer
# Edit main process, requires restart
```

### Working on Python Backend
Both frontends use the same Python backend. Changes to these files affect both:
- `document_organizer.py` - Core processing logic
- `ai_providers.py` - AI integrations
- `settings.py` - Configuration management
- `jd_system.py` - JD structure management
- `jd_builder.py` - JD interview builder

For Electron, also update `api_server.py` if adding new IPC methods.

## Build & Packaging

### Electron App Packaging
```bash
cd document-organizer-electron

# Package for current platform
npm run package

# Create distributable (DMG on macOS)
npm run make

# Build configuration in forge.config.ts
```

The Electron app bundles Python via PyInstaller. Build steps:
1. `npm run build:python` - Create Python executable
2. `npm run make` - Package Electron + Python together
