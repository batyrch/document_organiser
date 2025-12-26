# Document Organizer

Automatically organize your scanned documents into folders with AI-powered categorization using the [Johnny.Decimal](https://johnnydecimal.com/) system.

## How It Works

```
📁 inbox/                           📁 jd_documents/
├── scan001.pdf                     ├── 10-19 Finance/
├── receipt.jpg          →          │   └── 14 Receipts/
├── contract.pdf                    │       ├── 14.01 Amazon Laptop Receipt 2024.pdf
└── lab_results.pdf                 │       └── 14.02 TK Insurance Card 2024.pdf
                                    ├── 20-29 Medical/
                                    │   └── 21 Records/
                                    │       └── 21.01 Charité Blood Test Results 2024.pdf
                                    └── 30-39 Legal/
                                        └── 31 Contracts/
                                            └── 31.01 Vonovia Apartment Lease 2024.pdf
```

1. **Drop files or folders** into the inbox folder (subfolders are scanned recursively)
2. **Docling extracts** text from PDFs, images, Word docs, etc.
3. **AI analyzes** the content and categorizes using Johnny.Decimal
   - Folder names are used as context hints (e.g., "Salary Slips" folder → Work/Salary & Payments)
4. **Files are moved** to organized folders with descriptive names
5. **Metadata files** (.meta.json) are created with tags and summaries

## Key Features

- **Privacy-First**: All processing happens locally. Only extracted text is sent to AI providers
- **Multiple AI Providers**: Claude, GPT-4, AWS Bedrock, Ollama (100% offline), or keyword-only mode
- **Personalized JD System**: AI-powered interview builds a Johnny.Decimal structure tailored to your life
- **Web UI**: macOS Finder-inspired gallery view with drag-and-drop upload
- **Duplicate Detection**: SHA256 content hashing prevents filing the same document twice
- **Multi-Format Support**: PDF, images (PNG, JPG, TIFF), Office docs (DOCX, XLSX, PPTX), and text files

## Quick Start

### Option 1: One-Line Install (macOS/Linux)

```bash
git clone https://github.com/batyrch/document_organiser
cd document_organiser
./install.sh
```

The installer creates a virtual environment, installs dependencies, and sets up the `docorg` command.

**Run after installation:**
```bash
docorg
```

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/batyrch/document_organiser
cd document_organiser

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run ui.py
```

### Option 3: Docker

```bash
docker-compose up ui
# Access at http://localhost:8501
```

### AI Provider Setup

| Provider | Setup |
|----------|-------|
| **Claude Code CLI** | Works with Claude Max subscription - no API key needed |
| **Anthropic API** | `export ANTHROPIC_API_KEY="your-key"` |
| **OpenAI API** | `export OPENAI_API_KEY="your-key"` |
| **Ollama** | Install [Ollama](https://ollama.ai), run `ollama pull llama3.2` |
| **Keywords** | No setup - pattern matching only |

Visit **[batyrch.github.io/document_organiser](https://batyrch.github.io/document_organiser)** for interactive installation guide.

## Configuration

Edit `config.yaml` to customize paths and settings:

```yaml
paths:
  output_dir: ~/Documents/jd_documents
  inbox_dir: ~/Documents/jd_documents/00-09 System/01 Inbox

mode: claude-code  # claude-code, api, or keywords

ai:
  model: claude-sonnet-4-20250514  # Claude model for API mode

watch_interval: 5
```

For local overrides, copy to `config.local.yaml` (gitignored).

## Usage

### Recommended Workflow (UI-Based)

```bash
# Step 1: Preprocess - extract text + AI analysis
python document_organizer.py --preprocess --once

# Step 2: Open Web UI to manually classify and file documents
streamlit run ui.py
```

### Automatic Processing

```bash
# Watch mode (continuous)
python document_organizer.py

# One-time processing
python document_organizer.py --once

# Using API key instead of Claude Code CLI
python document_organizer.py --mode api

# Keyword-only mode (no AI)
python document_organizer.py --mode keywords

# Rebuild hash index for duplicate detection
python document_organizer.py --rebuild-index
```

## Web UI Features

Launch the UI with `streamlit run ui.py`

### Gallery View Layout (macOS Finder-inspired)

The UI uses a vertical stacked layout inspired by macOS Finder's Gallery View:

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

1. **Actions Toolbar** - Area/Category dropdowns + Move/Reanalyze/Delete/Reveal buttons
2. **Gallery Strip** - Horizontal scrolling thumbnails with ◀/▶ navigation
3. **Preview Section** - Large document preview (PDF/image/text)
4. **Classification Section** - Compact AI analysis display

### File Source Modes
- **Inbox Mode**: Scan default inbox folder for new documents
- **Browse Mode**: Scan any folder to view/manage existing documents
  - Toggle between modes in sidebar
  - Custom folder path with recursive option
  - **Navigation bar**: ◀ Back | ▶ Forward | ▲ Up | ▼ Down buttons
  - **Subfolder dropdown**: Navigate into subdirectories quickly
  - **Breadcrumb navigation**: Shows current path hierarchy

### iOS-Style Selection (like iOS Files app)
The UI uses a two-mode selection pattern inspired by iOS:

- **Browse Mode** (default): Click thumbnail in gallery → shows preview below
  - Actions toolbar always visible (disabled until file selected)
  - Single-file actions apply to currently previewed file

- **Selection Mode**: Tap "Select" button to enter
  - Checkboxes appear on gallery thumbnails
  - Click to toggle selection AND preview last clicked file
  - Select All / Clear buttons available
  - Toolbar Actions apply to all selected files
  - Tap "Done" to exit and clear selection

### Gallery Strip Features
- Paginated thumbnail strip showing **7 files at a time**
- Current file centered in view when possible
- ◀/▶ buttons scroll by 1 file at a time
- Current file highlighted with blue border
- Selected files highlighted in selection mode
- File count display (e.g., "3 of 15 files")
- **High-quality thumbnails**: 130x100px with sharpening for text-heavy documents

### Document Preview
- **PDF preview**: Embedded viewer (full width)
- **Image preview**: Large display area
- **Extracted text tab**: View OCR/extracted content
- **Analyze Now button**: Process files without analysis

### Classification Section
- Compact metadata row: Issuer | Type | Date | Confidence
- AI suggested category display
- Colored tag chips
- Collapsible summary expander

### Toolbar Actions
- **Area/Category dropdowns**: Pre-filled from AI analysis
- **Move**: Move file(s) to chosen category (auto-extracts text if missing)
- **Reanalyze**: Re-run text extraction (skips files that already have text)
- **Delete**: Remove file(s) with confirmation
- **Reveal**: Open in system file manager

> **Note:** Reanalyze is safe to run on all files - it only processes files missing `extracted_text` in their metadata, preserving all other fields.

### File Upload
- **Drag & drop upload**: Upload files directly in the UI
- Available in sidebar (always) and main area (when inbox is empty)
- Supports PDF, PNG, JPG, TIFF, BMP, DOCX, TXT

### Settings & Maintenance
- **Rebuild Hash Index**: Scan all files and rebuild duplicate detection index (Settings → About → Advanced)

### UI Polish
- **Lucide Icons**: Clean, modern SVG icons throughout the UI
- **Hand loading animation**: Animated hand indicator during processing
- **PDF thumbnails**: Visual previews in gallery strip (requires pymupdf)

## Personalized JD System Builder

Build a Johnny Decimal system tailored to YOUR life through an AI-powered interview.

### How It Works

1. Go to **Settings → JD System** tab
2. Click **"Build My JD System"**
3. AI asks about your work/life (4-6 questions)
4. Review the proposed structure
5. Accept & Create!

The AI learns about:
- Your work situation (employee, freelancer, student?)
- What documents you handle most
- Whether to separate personal/business
- Any special needs (hobbies, side projects)

### What Gets Created

- **jdex.json** - Your custom JD structure stored in `00-09 System/00 Index/`
- **Folder structure** - Created automatically
- **Keywords** - For auto-classification of future documents

### Johnny Decimal Constraints

The system enforces these rules (per official Johnny Decimal philosophy):
- Maximum **10 areas** (00-09 through 90-99)
- Maximum **10 categories** per area
- Area 00-09 reserved for System (Index, Inbox)

## Default Johnny.Decimal Categories

If you don't build a custom system, these defaults are used:

| Area | Categories |
|------|------------|
| **00-09 System** | Index, Inbox, Templates, Uncategorized |
| **10-19 Finance** | Banking, Taxes, Insurance, Receipts, Investments, Housing |
| **20-29 Medical** | Records, Insurance, Prescriptions, Vision, Bills |
| **30-39 Legal** | Contracts, Property, Identity, Warranties |
| **40-49 Work** | Employment, Expenses, Projects, Certifications, Salary & Payments |
| **50-59 Personal** | Education, Travel, Certificates, Memberships, Operation Manual, Health and Wellbeing, IDs |

> **Note:** Use **09 Uncategorized** for research papers, academic articles, or documents that don't fit other categories.

## Output Structure

For each processed file (flat structure - no sub-folders per document):

```
jd_documents/
└── 10-19 Finance/
    └── 14 Receipts/
        ├── 14.01 Amazon Laptop Receipt 2024.pdf
        ├── 14.01 Amazon Laptop Receipt 2024.pdf.meta.json
        ├── 14.01 Amazon Phone Case 2024.pdf       ← same issuer+year = same ID
        └── 14.02 TK Insurance Card 2024.pdf       ← different issuer = new ID
```

**Filename format:** `{JD_ID} {Issuer} {Document_Type} {Year}.ext`

**ID assignment rules:**
- Same issuer + same year = same JD ID
- Exact duplicates get `_1`, `_2` suffix

The `.meta.json` file contains:
```json
{
  "id": "14.01",
  "jd_area": "10-19 Finance",
  "jd_category": "14 Receipts",
  "document_type": "Laptop Receipt",
  "issuer": "Amazon",
  "tags": ["purchase", "electronics"],
  "summary": "Amazon purchase receipt for laptop...",
  "document_date": "2024-12-20",
  "extracted_text": "..."
}
```

## Supported File Types

- **PDF** (including scanned)
- **Images** (PNG, JPG, JPEG, TIFF, BMP)
- **Office** (DOCX, PPTX, XLSX)
- **Text** (TXT, HTML)

## Duplicate Detection

The system automatically detects duplicate files using content-based SHA256 hashing:

- **Hash index** (`.hash_index.json`) stores mappings for all organized files
- **On new file**: Checked against index before processing
- **Duplicate found**: Skipped and shows path to existing file
- **New file**: Processed and added to index

```bash
# First time or after manual changes: rebuild the index
python document_organizer.py --rebuild-index

# Or use the UI: Settings → About → Advanced → Rebuild Hash Index
```

## Tips

1. **Claude Code CLI**: Works with Claude Max subscription (no API key needed)
2. **Failed files**: Check the `_failed` folder for documents that couldn't be processed
3. **Metadata search**: Use `.meta.json` files to build a searchable index
4. **Browse Mode**: Use to view and reanalyze existing organized documents
5. **Batch import**: Drop a folder (e.g., "Salary Slips 2024") into inbox - folder name helps AI categorize
6. **Duplicate detection**: Run `--rebuild-index` after manually adding files to ensure duplicates are caught
7. **Backfill extracted text**: If older files are missing extracted text, use Browse Mode → Select All → Reanalyze Selected (only processes files without text)

## Requirements

- Python 3.10+

## Privacy

All document processing happens locally on your machine. Only extracted text is sent to AI providers (if using cloud AI). Use Ollama for 100% offline operation.

- **Website**: [batyrch.github.io/document_organiser](https://batyrch.github.io/document_organiser)
- **Privacy Policy**: [batyrch.github.io/document_organiser/privacy.html](https://batyrch.github.io/document_organiser/privacy.html)

## License

MIT License - see [LICENSE](LICENSE) for details.
