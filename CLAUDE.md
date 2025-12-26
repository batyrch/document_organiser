# Document Organizer - Claude Code Guide

## Overview

Automatically organize scanned documents using AI-powered categorization with the Johnny.Decimal system. Supports PDFs, images (with OCR), and Office documents.

## Project Structure

```
document_organiser/
├── document_organizer.py   # Main organizer script with JD integration
├── ui.py                   # Streamlit web UI for manual classification
├── icons.py                # Lucide Icons SVG definitions and helper functions
├── ai_providers.py         # AI provider integrations (Claude, OpenAI, Ollama, etc.)
├── settings.py             # Persistent settings management
├── device_auth.py          # Device authentication handling
├── preview_renames.py      # Migration preview script for renaming existing folders
├── migrate_to_jd.py        # Migration script for existing files
├── config.yaml             # Project settings (paths, mode, logging)
├── config.local.yaml       # Local overrides (gitignored, optional)
├── requirements.txt        # Python dependencies
├── README.md               # User documentation
├── CLAUDE.md               # This file - developer guide
├── .env                    # API keys only (ANTHROPIC_API_KEY)
├── install.sh              # macOS/Linux installer script
├── build_macos_native.py   # Build native .app bundle (simpler approach)
├── build_macos.py          # Build PyInstaller .app bundle (deprecated)
├── desktop/                # Desktop app files
│   ├── launch.sh           # Shell launcher for native app
│   └── launcher.py         # Python launcher for PyInstaller (deprecated)
├── pwa/                    # Landing page source files
│   ├── index.html          # Main landing page
│   ├── app.html            # Local app wrapper
│   └── privacy.html        # Privacy policy
└── docs/                   # GitHub Pages deployment folder
    ├── index.html          # Copy of pwa/index.html
    └── privacy.html        # Copy of pwa/privacy.html
```

## Johnny.Decimal System

Documents are organized into a flat structure within categories:
```
Area → Category → Files (with JD ID prefix)
Example: 10-19 Finance/14 Receipts/14.01 Amazon Laptop Receipt 2024.pdf
```

## Naming Convention

### File Names (Flat Structure)
Format: `{JD_ID} {Issuer} {Document Type} {Year}.{ext}`
- **JD_ID**: Johnny.Decimal ID (e.g., "14.01", "21.03")
- **Issuer**: Organization that created/issued the document (e.g., "Charité", "TK Insurance")
- **Document Type**: What the document IS (e.g., "Blood Test Results", "Employment Contract")
- **Year**: Document date year

Examples:
- `14.01 Amazon Laptop Receipt 2024.pdf`
- `21.01 Charité Blood Test Results 2024.pdf`
- `31.05 Vonovia Apartment Lease 2025.pdf`
- `41.03 AutoScout24 Employment Contract 2023.pdf`

### ID Assignment Rules
- **Same issuer + same year = Same JD ID**
  - `14.01 Amazon Laptop Receipt 2024.pdf`
  - `14.01 Amazon Phone Case 2024.pdf` ← same ID (same issuer+year)
- **Different issuer = New JD ID**
  - `14.02 TK Insurance Card 2024.pdf` ← new ID
- **Exact duplicates = Add suffix**
  - `14.01 Amazon Laptop Receipt 2024_1.pdf`

### Naming Rules
1. **Issuer always included** - who created/issued the document
2. **Document type required** - what the document IS
3. **Personal names excluded** - unless distinguishing family members' documents
4. **Year in filename** - extracted from document date

### JD Areas (Predefined)
- **00-09 System** - Index, Inbox, Templates, Uncategorized
- **10-19 Finance** - Banking, Taxes, Insurance, Receipts, Investments, Housing
- **20-29 Medical** - Records, Insurance, Prescriptions, Vision, Bills
- **30-39 Legal** - Contracts, Property, Identity, Warranties
- **40-49 Work** - Employment, Expenses, Projects, Certifications, Salary & Payments
- **50-59 Personal** - Education, Travel, Certificates, Memberships, Operation Manual, Health and Wellbeing, IDs
- **90-99 Archive** - By year (2024, 2023, etc.)

### Dynamic JD Folders (User-Created)
The system supports user-created areas and categories:
- **Create folders manually** following JD naming patterns (e.g., `60-69 Hobbies/61 Photography`)
- **Rename existing categories** - filesystem names take precedence over predefined names
- **UI dropdowns auto-update** to reflect user-created folders
- **Pattern requirements**:
  - Areas: `XX-XX Name` (e.g., `60-69 Hobbies`)
  - Categories: `XX Name` where XX is within the area range (e.g., `61 Photography` for area `60-69`)

## Key Files

### document_organizer.py
- `JD_AREAS` - Johnny.Decimal structure definition with keywords
- `categorize_with_keywords()` - Keyword-based JD categorization
- `categorize_with_claude_code()` - Claude CLI categorization
- `categorize_with_llm()` - Anthropic API categorization
- `generate_folder_descriptor()` - Generates descriptor from issuer + document type
- `generate_filename()` - Generates filename: `{JD_ID} {Issuer} {DocType} {Year}.ext`
- `organize_file()` - Creates flat JD structure (Area/Category/files) and moves files
- `get_or_create_jd_id()` - Manages ID assignment per issuer+year combination

**Dynamic folder scanning functions:**
- `is_valid_jd_area()` - Validates area folder naming pattern (e.g., `10-19 Finance`)
- `is_valid_jd_category()` - Validates category folder naming pattern (e.g., `14 Receipts`)
- `get_area_range()` - Extracts numeric range from area name (e.g., `10-19` → `(10, 19)`)
- `get_category_number()` - Extracts category number (e.g., `14 Receipts` → `14`)
- `category_belongs_to_area()` - Checks if category number is within area range
- `scan_jd_folders()` - Scans filesystem for JD-style folders
- `get_merged_jd_areas()` - Merges predefined JD_AREAS with user-created folders

**Duplicate detection functions:**
- `get_file_hash()` - SHA256 hash of file contents
- `build_hash_index()` - Scans output directory, hashes all files, saves to `.hash_index.json`
- `load_hash_index()` / `save_hash_index()` - Persistence for hash index
- `add_to_hash_index()` - Adds file hash after processing
- `find_duplicate_in_index()` - Checks if incoming file already exists (by content)

**Preprocessing functions:**
- `preprocess_file()` - Extract text + AI analysis, save to `.meta.json` (no move)
- `preprocess_inbox()` - Preprocess all files in inbox once (recursive, with folder hints)
- `watch_preprocess()` - Watch inbox and preprocess new files continuously
- `get_folder_hint()` - Extract subfolder name to use as context for AI categorization
- `get_analysis_path()` - Get path to `.meta.json` sidecar
- `load_analysis()` - Load existing analysis from JSON
- `save_analysis()` - Save analysis to JSON sidecar
- `has_analysis()` - Check if file has been analyzed

**Subfolder Support:**
- Inbox scanning is recursive - files in subfolders are found automatically
- Folder names are passed to AI as context hints (e.g., "Salary Slips" folder → 45 Salary & Payments)
- `folder_hint` parameter in `categorize_with_claude_code()` and `categorize_with_llm()`

### settings.py
- Persistent settings management stored in platform-specific config directory
- Settings stored in JSON at:
  - macOS: `~/Library/Application Support/DocumentOrganizer/settings.json`
  - Linux: `~/.config/DocumentOrganizer/settings.json`
  - Windows: `%APPDATA%/DocumentOrganizer/settings.json`
- Key functions:
  - `get_settings()` - Get global Settings instance
  - `Settings.get()` / `Settings.set()` - Read/write individual settings
  - `Settings.output_dir` / `Settings.inbox_dir` - Directory properties
  - `Settings.get_effective_provider()` - Auto-detect best AI provider
  - `Settings.create_directories()` - Create configured directories

### ui.py
- Streamlit web interface for manual classification
- **First-run Setup Wizard**: Guides new users through initial configuration
- **Settings Page**: Configure directories, AI providers, API keys
- **Navigation**: Sidebar radio to switch between Documents and Settings
- **Gallery View Layout** (macOS Finder-inspired):
  ```
  ┌──────────────────────────────────────────────────────────────────┐
  │  [Search bar]                                                     │
  ├──────────────────────────────────────────────────────────────────┤
  │  Actions: [Area ▼] [Category ▼] [Move] [Reanalyze] [Delete]      │
  ├──────────────────────────────────────────────────────────────────┤
  │  [Select/Done] ◀ [thumb1] [thumb2] [THUMB3*] [thumb4] ▶          │
  ├──────────────────────────────────────────────────────────────────┤
  │              LARGE PREVIEW (full width)                          │
  ├──────────────────────────────────────────────────────────────────┤
  │  Classification: Issuer | Type | Date | Tags | Summary           │
  └──────────────────────────────────────────────────────────────────┘
  ```
- `render_app()` - Main entry point, handles setup wizard vs normal app
- `render_settings_page()` - Full settings UI with tabs (Directories, AI, About)
  - **Advanced section**: Rebuild Hash Index button, Reset Settings
- `render_setup_wizard()` - First-run configuration wizard
- **Gallery View Components:**
  - `render_actions_toolbar()` - Full-width toolbar with Area/Category dropdowns and action buttons
  - `render_gallery_strip()` - Paginated thumbnail gallery showing 7 files at a time with scroll-by-1 navigation
  - `render_preview()` - Full-width file preview (PDF/Image/Text tabs)
  - `render_classification()` - Compact AI analysis display below preview
- **Thumbnail Generation** (`generate_thumbnail()`):
  - High-quality thumbnails at 130x100px display size
  - PDF rendering at 2.0x resolution for sharp text
  - UnsharpMask filter + contrast boost for text-heavy documents
  - Cached for 1 hour to improve performance
- `get_inbox_files()` - List files in inbox with analysis status
- `get_folder_files()` - List files in any folder with metadata (recursive option)
- `filter_files()` - Search/filter by metadata fields
- `reanalyze_file(file_path, skip_if_has_text=True)` - Re-run text extraction and analysis
  - Skips files that already have `extracted_text` in `.meta.json` (for bulk operations)
  - Updates `.meta.json` with newly extracted text (preserves other fields)
  - Use `skip_if_has_text=False` to force reanalysis (used by single-file "Re-analyze with AI" button)
- `hand_spinner()` - Context manager for animated hand loading indicator
- **Browse Mode**: Switch between Inbox and custom folder scanning
  - Subfolder dropdown for quick navigation into subdirectories
  - **Navigation bar**: Back/Forward/Up/Down buttons with history tracking
    - ◀ Back: Go to previous location (up to 50 locations in history)
    - ▶ Forward: Go forward after going back
    - ▲ Up: Go to parent folder
    - ▼ Down: Go into first subfolder

### preview_renames.py
- Scans existing jd_documents and proposes new names based on naming convention
- Generates markdown report for review before migration
- `--reanalyze` mode uses Claude Code CLI to analyze existing `.meta.json` files
- Falls back to document extraction only if no metadata exists
- Key functions:
  - `propose_new_name_from_ai()` - Uses Claude to suggest issuer + document_type from metadata
  - `propose_new_name()` - Fallback using existing metadata fields
  - `scan_jd_documents()` - Walks folder structure and generates proposals

### migrate_to_jd.py
- Migrates existing organized files to JD structure
- Maps old categories (financial/receipts) to JD (10-19 Finance/14 Receipts)
- Generates JDex index at `00-09 System/00 Index/00.00 Index.md`

## Configuration

Settings are loaded from `config.yaml` (with optional `config.local.yaml` for local overrides):

```yaml
# config.yaml
paths:
  output_dir: ~/Documents/jd_documents
  inbox_dir: ~/Documents/jd_documents/00-09 System/01 Inbox

mode: claude-code  # claude-code, api, or keywords

ai:
  model: claude-sonnet-4-20250514  # Claude model for API mode

watch_interval: 5

logging:
  level: INFO
  file: ""  # Optional log file path
```

**Priority order:** `config.local.yaml` > `config.yaml` > environment variables > defaults

## Running the Organizer

```bash
# Watch mode (continuous)
python document_organizer.py

# One-time processing
python document_organizer.py --once

# Keyword-only mode (no AI)
python document_organizer.py --mode keywords

# Rebuild hash index (for duplicate detection)
python document_organizer.py --rebuild-index
```

## Preprocessing Mode (Recommended Workflow)

The recommended workflow separates AI analysis from manual classification:

```bash
# Step 1: Preprocess - extract text + AI analysis (saves .meta.json files)
python document_organizer.py --preprocess

# Or preprocess once (no watching)
python document_organizer.py --preprocess --once

# Step 2: Open UI to manually classify and file documents
streamlit run ui.py
```

### How it works:
1. **Preprocess**: Extracts text and runs AI analysis, saves to `.meta.json` sidecar files
2. **Documents stay in inbox** until you manually classify them
3. **UI shows AI suggestions** pre-filled in the form
4. **You pick the final category** and click "Process & File"

### Metadata JSON format (`.meta.json`):
```json
{
  "jd_area": "20-29 Medical",
  "jd_category": "21 Records",
  "issuer": "Charité Hospital",
  "document_type": "Blood Test Results",
  "confidence": "high",
  "summary": "...",
  "extracted_text": "...",
  "analyzed_at": "2024-12-23T10:30:00"
}
```

## Web UI for Manual Classification

```bash
streamlit run ui.py
```

### UI Features

**File Source Modes:**
- **Inbox Mode**: Scan default inbox folder for new documents to classify
- **Browse Mode**: Scan any folder (with optional recursion) to view/manage existing documents
- Toggle between modes with radio button in sidebar
- Custom folder path input with recursive toggle
- **Breadcrumb navigation**: Shows current path hierarchy in browse mode
- **Navigation bar**: ◀ Back | ▶ Forward | ▲ Up | ▼ Down buttons with history

**Gallery View Layout (macOS Finder-inspired):**
The UI uses a vertical stacked layout inspired by macOS Finder's Gallery View:
1. **Actions Toolbar** (full width) - Area/Category dropdowns + Move/Reanalyze/Delete/Reveal buttons
2. **Gallery Strip** - Horizontal scrolling thumbnails with Select/Done toggle and ◀/▶ navigation
3. **Preview Section** (full width) - Large document preview with PDF viewer/image display/text tabs
4. **Classification Section** - Compact metadata display (Issuer, Type, Date, Confidence, Tags, Summary)

**iOS-Style Two-Mode Selection (like iOS Files app):**
- **Browse Mode** (default): Click thumbnail in gallery strip → shows preview below
  - Actions toolbar always visible (disabled until file selected)
  - Single-file actions apply to currently previewed file
- **Selection Mode**: Tap "Select" button → enters selection mode
  - Checkboxes appear on gallery thumbnails
  - Click thumbnails to toggle selection AND preview last clicked file
  - Select All / Clear buttons appear
  - Toolbar Actions apply to all selected files
  - Tap "Done" → exits selection mode and clears selection
- Based on [Apple iOS Files app pattern](https://support.apple.com/guide/iphone/organize-files-and-folders-iphab82e0798/ios)

**Gallery Strip Features:**
- Horizontal scrolling thumbnail strip (up to 50 files visible)
- Current file highlighted with blue border
- Selected files highlighted in selection mode
- ◀/▶ buttons for prev/next navigation
- File count display (e.g., "3 of 15 files" or "5 selected of 15 files")

**File Management:**
- **Colored tag chips**: Tags displayed with category-based colors (TAG_COLORS mapping)
- Search/filter by metadata (issuer, document_type, tags, category, text)
- **Thumbnails**: PDF and image thumbnails in gallery (requires pymupdf)

**Document Preview (Full Width):**
- PDF preview (embedded viewer)
- Image preview
- Extracted text display tab
- Large preview area for better document visibility

**Classification Section (Below Preview):**
- Compact metadata row: Issuer | Type | Date | Confidence
- AI suggested category display
- Colored tag chips
- Collapsible summary expander
- "Analyze Now" button if no analysis exists

**Toolbar Actions (Always Visible):**
- Area/Category dropdowns (pre-filled from AI analysis)
- Move - move file(s) to chosen category (auto-extracts text if missing)
- Reanalyze - re-run text extraction (skips files that already have text in bulk mode)
- Delete - remove file(s) with confirmation
- Reveal - open in system file manager
- All buttons disabled until file is selected (browse) or files are checked (selection)

**Text Extraction Behavior:**
- **Process & File**: Automatically extracts text if not already done (prevents empty `extracted_text` in `.meta.json`)
- **Move Selected**: Same - extracts text on-the-fly if missing
- **Reanalyze Selected**: Only processes files without `extracted_text`, skips files that already have it
- **Re-analyze with AI** (single file): Forces reanalysis regardless of existing text

**File Upload:**
- **Drag & drop upload**: Upload files directly in the UI
- Available in sidebar expander (always) and main area (when inbox is empty)
- Supports PDF, PNG, JPG, TIFF, BMP, DOCX, TXT
- Handles duplicate filenames with counter suffix

**Loading Animation:**
- Custom hand animation (CSS-based, inspired by codepen.io/r4ms3s/pen/XJqeKB)
- `hand_spinner()` context manager replaces `st.spinner()` throughout the app
- Shows animated tapping fingers during all processing operations

**UI Components (ui.py):**
- `TAG_COLORS` - Color mapping for JD areas and common tags
- `TAG_CHIPS_CSS` - Styles for chips, gallery cards, breadcrumbs, classification section, icon headers
- `render_tag_chips()` - Renders colored tag chips HTML
- `generate_thumbnail()` - Creates cached thumbnails for images/PDFs
- `render_breadcrumb()` - Renders folder navigation breadcrumb
- `get_file_icon()` - Returns Lucide SVG icon for file types
- `icon_title()` / `icon_subheader()` - Renders page titles/headers with Lucide icons
- `icon_label()` - Returns HTML for inline icon + text labels

**Gallery View CSS Classes:**
- `.gallery-strip-container` - Container for gallery strip
- `.gallery-strip` - Flexbox horizontal scroll container
- `.gallery-card` - Individual thumbnail card (100px width)
- `.gallery-card.current` - Highlighted current file
- `.gallery-card.selected` - Highlighted selected file (selection mode)
- `.gallery-card-thumb` - Thumbnail image container (88x70px)
- `.gallery-card-name` - Truncated filename below thumbnail
- `.actions-toolbar` - Toolbar container styling
- `.classification-section` - Classification section container
- `.classification-meta` - Metadata row flexbox

**Icons Module (icons.py):**
- `LUCIDE_ICONS` - Dictionary of 35+ Lucide icon SVG path definitions
- `lucide_icon(name, size, color)` - Renders Lucide icon as inline SVG HTML
- `file_type_icon(suffix, size)` - Maps file extensions to appropriate icons
- `status_icon(analyzed, size)` - Returns colored status indicator icons
- `icon_with_text(icon, text, size)` - Combines icon and text with proper alignment

## Running Migration

```bash
# Dry run first
python migrate_to_jd.py --dry-run

# Actual migration
python migrate_to_jd.py
```

## Preview Renames (Migration)

```bash
# Preview proposed renames (uses existing metadata summaries, no AI)
python preview_renames.py

# Save report to file
python preview_renames.py --output renames_report.md

# Re-analyze with AI (reads .meta.json, uses Claude Code to propose names)
python preview_renames.py --reanalyze

# Dry run - see what would be renamed without doing it
python preview_renames.py --reanalyze --execute --dry-run

# Actually rename the folders
python preview_renames.py --reanalyze --execute
```

### How `--reanalyze` works:
1. Checks if `.meta.json` exists for the document
2. If yes: sends `summary` + `extracted_text` to Claude Code CLI for naming
3. If no: extracts text from PDF/image first, then sends to Claude
4. Claude returns `{"issuer": "...", "document_type": "..."}` for folder naming

## Duplicate Detection

The system uses content-based hashing (SHA256) to detect duplicate files:

### How it works:
1. **Hash index** (`.hash_index.json`) stores hash → file path mapping for all organized files
2. **On new file**: Hash is calculated and checked against index before processing
3. **If duplicate found**: File is skipped (and deleted from inbox), shows path to existing file
4. **If new file**: Processed normally, hash added to index

### CLI Commands:
```bash
# Rebuild hash index from scratch (scan all files in output)
python document_organizer.py --rebuild-index

# Index is automatically updated when files are processed
```

### UI Access:
Settings → About → Advanced → "Rebuild Hash Index" button

### Files:
- `.hash_index.json` - Hash → path mapping (in output root)
- Automatically updated when files are organized
- Stale entries (deleted files) are cleaned up on rebuild

## Metadata Schema

Each document gets a `.meta.json` sidecar file:
```json
{
  "id": "14.03",
  "jd_area": "10-19 Finance",
  "jd_category": "14 Receipts",
  "document_type": "Laptop Receipt",
  "issuer": "Amazon",
  "subject_person": null,
  "document_date": "2024-12-20",
  "tags": ["receipt", "purchase"],
  "summary": "...",
  "extracted_text": "..."
}
```

## PWA Landing Page

**Live URL**: [batyrch.github.io/document_organiser](https://batyrch.github.io/document_organiser)

The `pwa/` folder contains source files for the public landing page, deployed via GitHub Pages from the `docs/` folder.

### Page Sections
- **Hero**: Logo, tagline, privacy badge, launch/get started buttons
- **How It Works**: 3-step visual (Drop files → AI categorizes → Organized library)
- **Features**: 6-card grid (AI Categorization, Johnny.Decimal, Privacy-First, Multi-Format, Metadata, Duplicate Detection)
- **Installation**: Platform-specific tabs (macOS, Windows, Linux) with copy-paste commands
- **App Status**: Real-time detection of localhost:8501, launch button when running
- **FAQ**: Accordion with common questions (privacy, AI providers, cost, requirements)
- **Footer**: Links to GitHub, privacy policy

### Features
- **Server Detection**: Automatically checks if `localhost:8501` is running
- **Visual Status**: Shows "App Running ✓" or "App Not Running" indicator
- **Launch Button**: Opens the Streamlit app when server is detected
- **Platform Tabs**: OS-specific installation instructions with syntax highlighting
- **Dark Mode**: Automatic based on system preference
- **Responsive**: Mobile-friendly layout
- **No External Dependencies**: Pure HTML/CSS/JS, no build step

### File Structure
```
pwa/                    # Source files (edit these)
├── index.html          # Main landing page (~1100 lines)
└── privacy.html        # Privacy policy page

docs/                   # GitHub Pages deployment (copy of pwa/)
├── index.html
└── privacy.html
```

### Deployment (GitHub Pages)
The site is deployed from the `docs/` folder on the `main` branch.

1. Edit files in `pwa/`
2. Copy changes to `docs/`:
   ```bash
   cp pwa/index.html docs/index.html
   cp pwa/privacy.html docs/privacy.html
   ```
3. Commit and push to `main`
4. GitHub Pages auto-deploys from `docs/`

### How It Works
1. User visits [batyrch.github.io/document_organiser](https://batyrch.github.io/document_organiser)
2. JavaScript checks if localhost:8501 responds
3. If running: "Launch App" button opens the Streamlit UI
4. If not running: Shows installation instructions with platform-specific tabs

### Privacy Page
`privacy.html` explains:
- What stays local (documents, files, metadata, settings)
- What may be sent externally (extracted text to AI providers)
- API key storage locations
- No tracking/analytics on the landing page

## Desktop App (macOS)

### Recommended: Native Installer

The recommended approach uses system Python with a virtual environment, avoiding PyInstaller bundling issues:

```bash
# Run the installer
./install.sh

# Launch the app
docorg
```

### How It Works

1. `install.sh` installs to `~/.local/share/document-organizer/`:
   - Copies application files
   - Creates a Python virtual environment
   - Installs all dependencies
   - Creates `docorg` launcher command in `~/.local/bin/`

2. `docorg` command:
   - Finds a free port
   - Starts Streamlit server from the venv
   - Opens browser automatically
   - Runs in Terminal (inherits user file permissions)

3. Optional macOS app (created during install):
   - Placed in `/Applications/Document Organizer.app`
   - Opens Terminal and runs `docorg`
   - Preserves file permissions (avoids sandboxing issues)

### Files

```
install.sh                    # One-line installer script
desktop/
├── launcher.py               # Legacy PyInstaller launcher (deprecated)
└── launch.sh                 # Shell script launcher for native app

~/.local/share/document-organizer/   # Installed app location
├── ui.py, document_organizer.py, etc.
├── requirements.txt
└── venv/                     # Python virtual environment

~/.local/bin/docorg           # Launcher command
```

### Why Not PyInstaller?

PyInstaller bundling has issues with Streamlit:
- `sys.executable` points to the bundled app, causing infinite process spawning
- Streamlit's internal multiprocessing breaks
- macOS sandbox blocks access to user folders (Documents, Downloads)

The native installer approach:
- Uses system Python (no bundling issues)
- Runs from Terminal (full file permissions)
- Smaller footprint (~1MB vs 800MB+)
- Easy updates (just re-run `install.sh`)

### Legacy: PyInstaller Build (Deprecated)

```bash
# Build with PyInstaller (may have issues)
python build_macos.py

# Or native app bundle (simpler, but still has sandbox issues)
python build_macos_native.py
```

## Dependencies

Install all dependencies with:
```bash
pip install -r requirements.txt
```

**Core:**
- streamlit (web UI)
- pyyaml (config parsing)
- python-dotenv (env vars)
- pillow (image handling)

**Document Processing:**
- docling (document conversion)
- pdfplumber (PDF fallback)
- pytesseract (OCR fallback)

**AI Providers:**
- anthropic (Claude API)
- openai (GPT API)
- boto3 (AWS Bedrock)
- requests (Ollama)

**Build:**
- pyinstaller (desktop app bundling)
