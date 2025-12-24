#!/usr/bin/env python3
"""
Migrate documents from old organized structure to new flat JD structure (v2).

This script:
1. Scans existing organized/ folder (category/subcategory/files)
2. Reads .meta.json files for summary and extracted_text
3. Uses AI (Claude Code CLI) to categorize and extract issuer/document_type
4. Creates flat structure: Area/Category/{JD_ID} {Issuer} {DocType} {Year}.ext
5. Copies files to new jd_organized_v2/ folder
6. Files AI can't categorize go to "uncat" folder for manual review

Usage:
    python flatten_to_v2.py --dry-run          # Preview changes
    python flatten_to_v2.py                    # Execute migration
    python flatten_to_v2.py --no-ai            # Skip AI, use static mapping

Source: /Users/batch/Documents/scanned_documents/organized
Dest:   /Users/batch/Documents/scanned_documents/jd_organized_v2
"""

import os
import re
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict


DEFAULT_SOURCE = "/Users/batch/Documents/scanned_documents/organized"
DEFAULT_DEST = "/Users/batch/Documents/scanned_documents/jd_organized_v2"
UNCAT_FOLDER = "00-09 System/09 Uncategorized"

# Supported document extensions
SUPPORTED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.docx', '.pptx', '.xlsx', '.txt', '.html'}


# Mapping from old (category, subcategory) to JD (area, category)
CATEGORY_MAPPING = {
    ("financial", "bank_statements"): ("10-19 Finance", "11 Banking"),
    ("financial", "financial_statements"): ("10-19 Finance", "11 Banking"),
    ("financial", "tax_documents"): ("10-19 Finance", "12 Taxes"),
    ("financial", "insurance"): ("10-19 Finance", "13 Insurance"),
    ("financial", "receipts"): ("10-19 Finance", "14 Receipts"),
    ("financial", "invoices"): ("10-19 Finance", "16 Bills"),
    ("financial", "contracts"): ("30-39 Legal", "31 Contracts"),
    ("medical", "records"): ("20-29 Medical", "21 Records"),
    ("medical", "lab_results"): ("20-29 Medical", "21 Records"),
    ("medical", "appointments"): ("20-29 Medical", "21 Records"),
    ("medical", "insurance"): ("20-29 Medical", "22 Insurance"),
    ("medical", "prescriptions"): ("20-29 Medical", "23 Prescriptions"),
    ("legal", "contracts"): ("30-39 Legal", "31 Contracts"),
    ("legal", "agreements"): ("30-39 Legal", "31 Contracts"),
    ("legal", "property"): ("30-39 Legal", "32 Property"),
    ("legal", "correspondence"): ("30-39 Legal", "31 Contracts"),
    ("legal", "court"): ("30-39 Legal", "31 Contracts"),
    ("personal", "identification"): ("30-39 Legal", "33 Identity"),
    ("personal", "correspondence"): ("50-59 Personal", "54 Memberships"),
    ("personal", "certificates"): ("50-59 Personal", "53 Certificates"),
    ("work", "hr"): ("40-49 Work", "41 Employment"),
    ("work", "correspondence"): ("40-49 Work", "41 Employment"),
    ("work", "reports"): ("40-49 Work", "43 Projects"),
    ("work", "projects"): ("40-49 Work", "43 Projects"),
    ("work", "documentation"): ("40-49 Work", "43 Projects"),
    ("work", "contracts"): ("40-49 Work", "41 Employment"),
    ("education", "certificates"): ("50-59 Personal", "51 Education"),
    ("education", "assignments"): ("50-59 Personal", "51 Education"),
    ("education", "notes"): ("50-59 Personal", "51 Education"),
    ("education", "agreements"): ("50-59 Personal", "51 Education"),
    ("education", "transcripts"): ("50-59 Personal", "51 Education"),
    ("other", "miscellaneous"): ("50-59 Personal", "54 Memberships"),
}

# Johnny.Decimal Areas and Categories for AI prompt
JD_AREAS = {
    "10-19 Finance": ["11 Banking", "12 Taxes", "13 Insurance", "14 Receipts", "15 Investments", "16 Bills"],
    "20-29 Medical": ["21 Records", "22 Insurance", "23 Prescriptions", "24 Dental", "25 Vision"],
    "30-39 Legal": ["31 Contracts", "32 Property", "33 Identity", "34 Warranties"],
    "40-49 Work": ["41 Employment", "42 Expenses", "43 Projects", "44 Certifications"],
    "50-59 Personal": ["51 Education", "52 Travel", "53 Certificates", "54 Memberships"],
}


def categorize_with_ai(metadata: dict) -> dict:
    """Use Claude Code CLI to categorize and extract naming info from metadata.

    Returns dict with: jd_area, jd_category, issuer, document_type, date_mentioned
    Returns None if AI fails.
    """
    # Get text content from metadata
    text = metadata.get("extracted_text", "")
    summary = metadata.get("summary", "")

    # Combine available text
    content = ""
    if summary:
        content += f"Summary: {summary}\n\n"
    if text:
        # Truncate text if too long
        max_chars = 5000
        content += f"Document text:\n{text[:max_chars]}"

    if not content.strip():
        return None

    prompt = f"""You are a document categorization assistant using the Johnny.Decimal system.

Available Johnny.Decimal areas and categories:
{json.dumps(JD_AREAS, indent=2)}

Analyze this document and categorize it.

{content}

IMPORTANT naming rules:
- "document_type" should describe WHAT the document is (e.g., "Blood Test Results", "Employment Contract", "Insurance Card")
- "issuer" should be the organization/entity that CREATED or ISSUED the document (e.g., "Charité Hospital", "TK Insurance", "Amazon")
- Do NOT use personal names as issuer (the issuer is the organization, not the person the document is about)

Respond with ONLY valid JSON in this exact format (no other text):
{{"jd_area": "one of the areas like 10-19 Finance", "jd_category": "one of the categories like 14 Receipts", "document_type": "specific type like Blood Test Results or Employment Contract", "issuer": "organization that created/issued the document", "date_mentioned": "YYYY-MM-DD or null", "confidence": "high/medium/low"}}"""

    try:
        # Use Claude Code CLI with --print flag for non-interactive output
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"  ⚠️  Claude Code failed: {result.stderr}")
            return None

        result_text = result.stdout.strip()

        # Parse JSON from response
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]

        # Try to find JSON in the response
        json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group()

        ai_result = json.loads(result_text)

        # Validate required fields
        if ai_result.get("jd_area") and ai_result.get("jd_category"):
            return ai_result
        else:
            print(f"  ⚠️  AI response missing required fields")
            return None

    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Claude Code timed out")
        return None
    except FileNotFoundError:
        print("  ⚠️  Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return None
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Failed to parse AI response: {e}")
        return None
    except Exception as e:
        print(f"  ⚠️  AI categorization failed: {e}")
        return None


def get_jd_mapping(category: str, subcategory: str) -> tuple:
    """Map old category/subcategory to JD area/category."""
    key = (category.lower(), subcategory.lower())
    if key in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[key]
    # Default fallback
    return ("50-59 Personal", "54 Memberships")


def extract_year_from_metadata(metadata: dict) -> str:
    """Extract year from metadata."""
    date_mentioned = metadata.get("document_date") or metadata.get("date_mentioned")
    if date_mentioned:
        try:
            return date_mentioned[:4]
        except (TypeError, IndexError):
            pass

    organized_date = metadata.get("organized_date")
    if organized_date:
        try:
            return organized_date[:4]
        except (TypeError, IndexError):
            pass

    return str(datetime.now().year)


def extract_issuer_from_metadata(metadata: dict, filename: str) -> str:
    """Extract issuer from metadata or filename."""
    # Try entities first (usually the organization)
    entities = metadata.get("entities", [])
    if entities:
        # Use first entity as issuer
        return entities[0]

    # Try to extract from filename (format: YYYYMMDD_Issuer_Name.pdf)
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) == 8:
        # Remove date prefix, join remaining parts
        return " ".join(parts[1:])

    return ""


def extract_doctype_from_metadata(metadata: dict) -> str:
    """Extract document type from metadata."""
    # Check if there's an explicit document_type
    doc_type = metadata.get("document_type", "")
    if doc_type:
        return doc_type

    # Derive from subcategory
    subcategory = metadata.get("subcategory", "")
    if subcategory:
        # Convert "bank_statements" to "Bank Statement"
        return subcategory.replace("_", " ").title().rstrip("s")  # Remove plural

    return "Document"


def clean_for_filename(text: str, max_length: int = 50) -> str:
    """Clean text for use in filename."""
    if not text:
        return ""

    # Remove/replace problematic characters
    text = text.strip().rstrip(".,;:")
    text = text.replace("/", "_").replace("\\", "_").replace(":", "_")
    text = text.replace("  ", " ")

    return text[:max_length]


def generate_flat_filename(jd_id: str, issuer: str, doc_type: str, year: str, ext: str) -> str:
    """Generate the new flat filename format.

    Format: {JD_ID} {Issuer} {Document_Type} {Year}.ext
    Example: 14.01 Woolworth GmbH Receipt 2025.pdf
    """
    parts = []

    if issuer:
        parts.append(clean_for_filename(issuer, 30))
    if doc_type:
        parts.append(clean_for_filename(doc_type, 30))

    if not parts:
        parts.append("Document")

    descriptor = " ".join(parts)

    return f"{jd_id} {descriptor} {year}{ext}"


def scan_existing_structure(source_dir: str) -> list:
    """Scan all documents in the old organized structure."""
    files = []
    source_path = Path(source_dir)

    if not source_path.exists():
        print(f"Source directory not found: {source_dir}")
        return []

    # Walk through all files
    for file_path in source_path.rglob("*"):
        if not file_path.is_file():
            continue

        # Skip metadata files, we'll find them via the document
        if file_path.suffix == ".json":
            continue

        # Skip unsupported files
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        # Skip _failed folder
        if "_failed" in str(file_path):
            continue

        # Try to find corresponding .meta.json
        meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
        metadata = {}

        if meta_path.exists():
            try:
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"  Warning: Could not read metadata for {file_path.name}: {e}")

        # Extract category/subcategory from path
        # Expected: source/category/subcategory/file.pdf
        rel_path = file_path.relative_to(source_path)
        path_parts = rel_path.parts

        if len(path_parts) >= 2:
            old_category = path_parts[0]      # e.g., "financial"
            old_subcategory = path_parts[1]   # e.g., "receipts"
        else:
            old_category = metadata.get("category", "other")
            old_subcategory = metadata.get("subcategory", "miscellaneous")

        files.append({
            "doc_path": file_path,
            "meta_path": meta_path if meta_path.exists() else None,
            "metadata": metadata,
            "old_category": old_category,
            "old_subcategory": old_subcategory,
        })

    return files


def migrate_to_flat(source_dir: str, dest_dir: str, dry_run: bool = False, use_ai: bool = True) -> dict:
    """Migrate files from old structure to flat JD structure.

    Args:
        source_dir: Source directory with old organized files
        dest_dir: Destination directory for flat JD structure
        dry_run: If True, show what would be done without making changes
        use_ai: If True, use AI for categorization and naming
    """
    print(f"\nScanning source directory: {source_dir}")
    files = scan_existing_structure(source_dir)
    print(f"Found {len(files)} documents to migrate\n")

    if not files:
        return {"migrated": 0, "errors": 0, "uncategorized": 0}

    # Track IDs per category for assignments
    # Same issuer + same year = same JD ID
    id_tracker = defaultdict(lambda: {"next_id": 1, "assigned": {}})

    migrated = 0
    errors = 0
    uncategorized = 0

    total = len(files)
    for idx, file_info in enumerate(files, 1):
        doc_path = file_info["doc_path"]
        meta_path = file_info["meta_path"]
        metadata = file_info["metadata"]
        old_category = file_info["old_category"]
        old_subcategory = file_info["old_subcategory"]

        print(f"\n[{idx}/{total}] Processing: {doc_path.name}")

        # Try AI categorization first if enabled
        ai_result = None
        if use_ai and metadata:
            print(f"  🤖 Analyzing with AI...")
            ai_result = categorize_with_ai(metadata)

        if ai_result:
            # Use AI results
            jd_area = ai_result.get("jd_area")
            jd_category = ai_result.get("jd_category")
            issuer = ai_result.get("issuer", "")
            doc_type = ai_result.get("document_type", "")
            date_mentioned = ai_result.get("date_mentioned")

            # Extract year from AI date or metadata
            if date_mentioned:
                year = date_mentioned[:4]
            else:
                year = extract_year_from_metadata(metadata)

            print(f"  ✅ AI: {jd_area}/{jd_category} | {issuer} | {doc_type}")
        elif use_ai:
            # AI failed - move to uncategorized folder
            print(f"  ⚠️  AI couldn't categorize - moving to uncategorized")
            jd_area = "00-09 System"
            jd_category = "09 Uncategorized"
            issuer = extract_issuer_from_metadata(metadata, doc_path.name)
            doc_type = extract_doctype_from_metadata(metadata)
            year = extract_year_from_metadata(metadata)
            uncategorized += 1
        else:
            # No AI - use static mapping
            jd_area, jd_category = get_jd_mapping(old_category, old_subcategory)
            issuer = extract_issuer_from_metadata(metadata, doc_path.name)
            doc_type = extract_doctype_from_metadata(metadata)
            year = extract_year_from_metadata(metadata)

        # Get category number (e.g., "14" from "14 Receipts")
        cat_num = jd_category.split()[0] if jd_category else "09"

        # Assign JD ID based on issuer+year (same issuer+year = same ID)
        issuer_key = f"{issuer or 'Unknown'}_{year}"

        if issuer_key in id_tracker[jd_category]["assigned"]:
            jd_id = id_tracker[jd_category]["assigned"][issuer_key]
        else:
            id_num = id_tracker[jd_category]["next_id"]
            jd_id = f"{cat_num}.{id_num:02d}"
            id_tracker[jd_category]["assigned"][issuer_key] = jd_id
            id_tracker[jd_category]["next_id"] += 1

        # Generate new filename
        new_filename = generate_flat_filename(jd_id, issuer, doc_type, year, doc_path.suffix)

        # Destination path
        dest_category_path = Path(dest_dir) / jd_area / jd_category
        dest_doc_path = dest_category_path / new_filename

        # Handle duplicates - add suffix
        counter = 1
        base_name = dest_doc_path.stem
        while dest_doc_path.exists() or (not dry_run and dest_category_path.exists() and any(
            f.name == dest_doc_path.name for f in dest_category_path.glob("*") if f.is_file()
        )):
            dest_doc_path = dest_category_path / f"{base_name}_{counter}{doc_path.suffix}"
            counter += 1
            if counter > 100:  # Safety limit
                break

        try:
            if dry_run:
                print(f"  [DRY RUN] -> {jd_area}/{jd_category}/{dest_doc_path.name}")
            else:
                # Create destination directory
                dest_category_path.mkdir(parents=True, exist_ok=True)

                # Copy document
                shutil.copy2(doc_path, dest_doc_path)

                # Update and copy metadata
                updated_metadata = {
                    **metadata,
                    "id": jd_id,
                    "jd_area": jd_area,
                    "jd_category": jd_category,
                    "issuer": issuer,
                    "document_type": doc_type,
                    "current_filename": dest_doc_path.name,
                    "original_filename": metadata.get("original_filename", doc_path.name),
                    "migrated_at": datetime.now().isoformat(),
                    "old_category": old_category,
                    "old_subcategory": old_subcategory,
                    "ai_categorized": ai_result is not None,
                }

                dest_meta_path = dest_doc_path.with_suffix(dest_doc_path.suffix + ".meta.json")
                with open(dest_meta_path, 'w') as f:
                    json.dump(updated_metadata, f, indent=2, ensure_ascii=False)

                print(f"  📁 Migrated: {jd_area}/{jd_category}/{dest_doc_path.name}")

            migrated += 1

        except Exception as e:
            print(f"  ❌ Error migrating {doc_path.name}: {e}")
            errors += 1

    return {
        "migrated": migrated,
        "errors": errors,
        "uncategorized": uncategorized,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Migrate documents to flat JD structure (v2) with AI categorization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python flatten_to_v2.py --dry-run          # Preview changes with AI
    python flatten_to_v2.py                    # Execute migration with AI
    python flatten_to_v2.py --no-ai            # Skip AI, use static mapping
    python flatten_to_v2.py --source /old --dest /new
        """
    )

    parser.add_argument(
        "--source", "-s",
        default=DEFAULT_SOURCE,
        help=f"Source directory with old organized files (default: {DEFAULT_SOURCE})"
    )
    parser.add_argument(
        "--dest", "-d",
        default=DEFAULT_DEST,
        help=f"Destination directory for flat JD structure (default: {DEFAULT_DEST})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI categorization, use static category mapping instead"
    )

    args = parser.parse_args()

    use_ai = not args.no_ai

    print("=" * 70)
    print("Migration: Old Structure -> Flat JD Structure (v2)")
    print("=" * 70)
    print(f"Source: {args.source}")
    print(f"Dest:   {args.dest}")
    if args.dry_run:
        print("Mode:   DRY RUN (no changes will be made)")
    else:
        print("Mode:   EXECUTE")
    if use_ai:
        print("AI:     ENABLED (using Claude Code CLI for categorization)")
    else:
        print("AI:     DISABLED (using static category mapping)")
    print("=" * 70)
    print()
    print("New filename format: {JD_ID} {Issuer} {DocType} {Year}.ext")
    print("Example: 14.01 Woolworth GmbH Receipt 2025.pdf")
    print()
    print("ID Assignment: Same issuer + same year = same JD ID")
    if use_ai:
        print("Uncategorized: Files AI can't process go to 00-09 System/09 Uncategorized")
    print()
    print("-" * 70)

    result = migrate_to_flat(args.source, args.dest, args.dry_run, use_ai)

    print()
    print("=" * 70)
    print("Migration Complete!")
    print(f"  Migrated:      {result['migrated']} files")
    print(f"  Errors:        {result['errors']}")
    print(f"  Uncategorized: {result['uncategorized']}")
    print("=" * 70)

    if not args.dry_run and result['migrated'] > 0:
        print(f"\nFiles migrated to: {args.dest}")
        if result['uncategorized'] > 0:
            print(f"\n⚠️  {result['uncategorized']} files need manual review in:")
            print(f"   {args.dest}/00-09 System/09 Uncategorized/")
        print("Review the new structure, then you can delete the old folder if satisfied.")


if __name__ == "__main__":
    main()
