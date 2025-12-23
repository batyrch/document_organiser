# Document Organizer - Claude Code Guide

## Overview

This project automatically organizes scanned documents using AI-powered categorization with the Johnny.Decimal system.

## Project Structure

```
document_organiser/
├── document_organizer.py   # Main organizer script with JD integration
├── preview_renames.py      # Migration preview script for renaming existing folders
├── migrate_to_jd.py        # Migration script for existing files
├── README.md               # User documentation
└── .env                    # Environment variables (ANTHROPIC_API_KEY, INBOX_DIR, OUTPUT_DIR)
```

## Johnny.Decimal System

Documents are organized into a hierarchical structure:
```
Area → Category → ID Folder → Files
Example: 10-19 Finance/14 Receipts/14.01 Amazon Laptop Receipt 2024/20241220_amazon_laptop_receipt.pdf
```

## Naming Convention

### Folder Names
Format: `{JD_ID} {Issuer} {Document Type} {Year}`
- **Issuer**: Organization that created/issued the document (e.g., "Charité", "TK Insurance")
- **Document Type**: What the document IS (e.g., "Blood Test Results", "Employment Contract")
- **Year**: Document date year

Examples:
- `21.01 Charité Blood Test Results 2024`
- `31.05 Vonovia Apartment Lease 2025`
- `41.03 AutoScout24 Employment Contract 2023`

### File Names
Format: `{YYYYMMDD}_{issuer}_{document_type}.{ext}`

Examples:
- `20241220_charite_blood_test_results.pdf`
- `20241115_vonovia_apartment_lease.pdf`

### Naming Rules
1. **Issuer always included** - who created/issued the document
2. **Document type required** - what the document IS
3. **Personal names excluded** - unless distinguishing family members' documents
4. **Year in folder** - extracted from document date

### JD Areas
- **00-09 System** - Index, Inbox, Templates
- **10-19 Finance** - Banking, Taxes, Insurance, Receipts, Investments, Bills
- **20-29 Medical** - Records, Insurance, Prescriptions, Dental, Vision
- **30-39 Legal** - Contracts, Property, Identity, Warranties
- **40-49 Work** - Employment, Expenses, Projects, Certifications
- **50-59 Personal** - Education, Travel, Certificates, Memberships
- **90-99 Archive** - By year (2024, 2023, etc.)

## Key Files

### document_organizer.py
- `JD_AREAS` - Johnny.Decimal structure definition with keywords
- `categorize_with_keywords()` - Keyword-based JD categorization
- `categorize_with_claude_code()` - Claude CLI categorization
- `categorize_with_llm()` - Anthropic API categorization
- `generate_folder_descriptor()` - Generates folder name from issuer + document type
- `generate_filename()` - Generates filename from date + issuer + document type
- `organize_file()` - Creates JD folder structure and moves files
- `get_or_create_jd_id()` - Manages ID assignment per category

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

## Default Paths

- **JD Output**: `/Users/batch/Documents/scanned_documents/jd_documents`
- **JD Inbox**: `/Users/batch/Documents/scanned_documents/jd_documents/00-09 System/01 Inbox`

## Running the Organizer

```bash
# Activate virtual environment
source docling-env/bin/activate

# Watch mode (continuous)
python document_organizer.py

# One-time processing
python document_organizer.py --once

# Keyword-only mode (no AI)
python document_organizer.py --mode keywords
```

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
