# Document Organizer

Automatically organize your scanned documents into folders with AI-powered categorization.

## How It Works

```
📁 inbox/                    📁 organized/
├── scan001.pdf      →      ├── financial/
├── receipt.jpg              │   ├── invoices/
├── contract.pdf             │   └── receipts/
└── lab_results.pdf          │       └── 20241220_amazon_purchase.jpg
                             ├── medical/
                             │   └── lab_results/
                             │       └── 20241215_bloodwork.pdf
                             └── legal/
                                 └── contracts/
                                     └── 20241201_lease_agreement.pdf
```

1. **Drop files** into the `inbox` folder
2. **Docling extracts** text from PDFs, images, Word docs, etc.
3. **AI analyzes** the content and picks a category
4. **Files are moved** to organized folders with descriptive names
5. **Metadata files** (.meta.json) are created with tags and summaries

## Installation

```bash
# 1. Install dependencies
pip install docling anthropic pdfplumber pytesseract pillow

# 2. (Optional) For better OCR on scanned docs
# macOS: brew install tesseract
# Ubuntu: sudo apt install tesseract-ocr
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki

# 3. Set your API key (optional - enables smart categorization)
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage

### Watch Mode (Continuous)
```bash
python document_organizer.py --inbox ./inbox --output ./organized
```
Files dropped into `inbox` will be automatically processed.

### One-Time Processing
```bash
python document_organizer.py --inbox ./inbox --output ./organized --once
```

### Without AI (Keyword Matching Only)
```bash
python document_organizer.py --inbox ./inbox --output ./organized --no-llm
```
No API key needed - uses simple keyword matching.

## Default Categories

| Category | Subcategories |
|----------|---------------|
| **financial** | invoices, receipts, tax_documents, bank_statements, contracts |
| **medical** | prescriptions, lab_results, insurance, appointments, records |
| **legal** | contracts, agreements, correspondence, court, property |
| **personal** | identification, correspondence, certificates, photos |
| **work** | reports, presentations, correspondence, projects, hr |
| **education** | transcripts, certificates, assignments, notes |
| **other** | miscellaneous |

## Customizing Categories

Edit `DEFAULT_CATEGORIES` in the script to add your own:

```python
DEFAULT_CATEGORIES = {
    "my_custom_category": {
        "subcategories": ["sub1", "sub2"],
        "keywords": ["keyword1", "keyword2"]
    },
    # ...
}
```

## Output Structure

For each processed file, you get:

```
organized/
└── financial/
    └── receipts/
        ├── 20241220_amazon_purchase.pdf      # Renamed file
        └── 20241220_amazon_purchase.pdf.meta.json  # Metadata
```

The `.meta.json` file contains:
```json
{
  "original_filename": "scan001.pdf",
  "category": "financial",
  "subcategory": "receipts",
  "tags": ["purchase", "amazon", "electronics"],
  "summary": "Amazon purchase receipt for electronics...",
  "entities": ["Amazon", "John Doe"],
  "date_mentioned": "2024-12-20"
}
```

## Supported File Types

- **PDF** (including scanned)
- **Images** (PNG, JPG, JPEG, TIFF, BMP)
- **Office** (DOCX, PPTX, XLSX)
- **Text** (TXT, HTML)

## Tips

1. **Better OCR**: Install Tesseract for best results with scanned documents
2. **API Key**: Using Claude API gives much better categorization than keywords alone
3. **Failed files**: Check the `_failed` folder for documents that couldn't be processed
4. **Metadata search**: Use the `.meta.json` files to build a searchable index
