# Document Organizer - Claude Code Guide

## Overview

Automatically organize scanned documents using AI-powered categorization with the Johnny.Decimal system. Supports PDFs, images (with OCR), and Office documents.

## Project Structure

```
document_organiser/
├── document_organizer.py   # Main organizer script with JD integration
├── ui.py                   # Streamlit web UI for manual classification
├── preview_renames.py      # Migration preview script for renaming existing folders
├── migrate_to_jd.py        # Migration script for existing files
├── config.yaml             # Project settings (paths, mode, logging)
├── config.local.yaml       # Local overrides (gitignored, optional)
├── README.md               # User documentation
└── .env                    # API keys only (ANTHROPIC_API_KEY)
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

### JD Areas
- **00-09 System** - Index, Inbox, Templates, Uncategorized
- **10-19 Finance** - Banking, Taxes, Insurance, Receipts, Investments, Housing
- **20-29 Medical** - Records, Insurance, Prescriptions, Vision, Bills
- **30-39 Legal** - Contracts, Property, Identity, Warranties
- **40-49 Work** - Employment, Expenses, Projects, Certifications, Salary & Payments
- **50-59 Personal** - Education, Travel, Certificates, Memberships, Operation Manual, Health and Wellbeing, IDs
- **90-99 Archive** - By year (2024, 2023, etc.)

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

**Preprocessing functions:**
- `preprocess_file()` - Extract text + AI analysis, save to `.analysis.json` (no move)
- `preprocess_inbox()` - Preprocess all files in inbox once (recursive, with folder hints)
- `watch_preprocess()` - Watch inbox and preprocess new files continuously
- `get_folder_hint()` - Extract subfolder name to use as context for AI categorization
- `get_analysis_path()` - Get path to `.analysis.json` sidecar
- `load_analysis()` - Load existing analysis from JSON
- `save_analysis()` - Save analysis to JSON sidecar
- `has_analysis()` - Check if file has been analyzed

**Subfolder Support:**
- Inbox scanning is recursive - files in subfolders are found automatically
- Folder names are passed to AI as context hints (e.g., "Salary Slips" folder → 45 Salary & Payments)
- `folder_hint` parameter in `categorize_with_claude_code()` and `categorize_with_llm()`

### ui.py
- Streamlit web interface for manual classification
- `get_inbox_files()` - List files in inbox with analysis status
- `get_folder_files()` - List files in any folder with metadata (recursive option)
- `filter_files()` - Search/filter by metadata fields
- `reanalyze_file()` - Delete and re-run analysis
- `hand_spinner()` - Context manager for animated hand loading indicator
- **Browse Mode**: Switch between Inbox and custom folder scanning
  - Subfolder dropdown for quick navigation into subdirectories

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
```

## Preprocessing Mode (Recommended Workflow)

The recommended workflow separates AI analysis from manual classification:

```bash
# Step 1: Preprocess - extract text + AI analysis (saves .analysis.json files)
python document_organizer.py --preprocess

# Or preprocess once (no watching)
python document_organizer.py --preprocess --once

# Step 2: Open UI to manually classify and file documents
streamlit run ui.py
```

### How it works:
1. **Preprocess**: Extracts text and runs AI analysis, saves to `.analysis.json` sidecar files
2. **Documents stay in inbox** until you manually classify them
3. **UI shows AI suggestions** pre-filled in the form
4. **You pick the final category** and click "Process & File"

### Analysis JSON format (`.analysis.json`):
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

**File Management:**
- File list with metadata status (✅ has metadata, ⏳ pending)
- Checkbox selection for bulk operations (Select All uses versioned keys for proper state sync)
- Search/filter by metadata (issuer, document_type, tags, category, text)
- Navigation (Prev/Next buttons, file counter)

**Document View:**
- PDF preview (embedded viewer)
- Image preview
- Extracted text display tab
- AI analysis panel with all metadata fields

**Classification:**
- AI suggestion pre-filled in form
- Manual override for area, category, issuer, document type, date, tags
- Re-analyze button to re-run AI on current file

**Bulk Actions:**
- Select All / Clear Selection
- Move Selected - move multiple files to chosen category
- Reanalyze Selected - re-run AI on selected files
- Delete Selected - remove selected files

**Loading Animation:**
- Custom hand animation (CSS-based, inspired by codepen.io/r4ms3s/pen/XJqeKB)
- `hand_spinner()` context manager replaces `st.spinner()` throughout the app
- Shows animated tapping fingers during all processing operations

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

## Dependencies

- docling (document conversion)
- anthropic (Claude API)
- pdfplumber (PDF fallback)
- pytesseract (OCR fallback)
- python-dotenv
- Pillow
- streamlit (web UI)
