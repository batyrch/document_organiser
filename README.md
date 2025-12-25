# Document Organizer

Automatically organize your scanned documents into folders with AI-powered categorization using the Johnny.Decimal system.

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

## Installation

```bash
# 1. Install dependencies
pip install docling anthropic pdfplumber pytesseract pillow python-dotenv streamlit pyyaml

# 2. (Optional) For better OCR on scanned docs
# macOS: brew install tesseract
# Ubuntu: sudo apt install tesseract-ocr
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki

# 3. Configure paths in config.yaml (or copy to config.local.yaml for local overrides)
# 4. Set your API key (optional - Claude Code CLI can use Max subscription)
export ANTHROPIC_API_KEY="your-key-here"
```

## Configuration

Edit `config.yaml` to customize paths and settings:

```yaml
paths:
  output_dir: ~/Documents/jd_documents
  inbox_dir: ~/Documents/jd_documents/00-09 System/01 Inbox

mode: claude-code  # claude-code, api, or keywords
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

### File Source Modes
- **Inbox Mode**: Scan default inbox folder for new documents
- **Browse Mode**: Scan any folder to view/manage existing documents
  - Toggle between modes in sidebar
  - Custom folder path with recursive option
  - **Subfolder dropdown**: Navigate into subdirectories quickly

### Document Management
- File list with metadata status (✅ has metadata, ⏳ pending)
- PDF and image preview
- Extracted text display
- AI analysis panel with all metadata fields

### Classification
- AI suggestion pre-filled in form
- Manual override for area, category, issuer, document type, date, tags
- Re-analyze button for individual files

### Bulk Operations
- Select multiple files with checkboxes (Select All / Clear Selection)
- Move Selected - batch move to chosen category
- Reanalyze Selected - re-run AI on selected files
- Delete Selected - remove selected files

### Settings & Maintenance
- **Rebuild Hash Index**: Scan all files and rebuild duplicate detection index (Settings → About → Advanced)

### UI Polish
- **Hand loading animation**: Animated hand indicator during processing operations

## Johnny.Decimal Categories

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

1. **Better OCR**: Install Tesseract for best results with scanned documents
2. **Claude Code CLI**: Works with Claude Max subscription (no API key needed)
3. **Failed files**: Check the `_failed` folder for documents that couldn't be processed
4. **Metadata search**: Use `.meta.json` files to build a searchable index
5. **Browse Mode**: Use to view and reanalyze existing organized documents
6. **Batch import**: Drop a folder (e.g., "Salary Slips 2024") into inbox - folder name helps AI categorize
7. **Duplicate detection**: Run `--rebuild-index` after manually adding files to ensure duplicates are caught
