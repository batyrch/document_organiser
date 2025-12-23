#!/usr/bin/env python3
"""
Migrate existing organized documents to Johnny.Decimal structure.

This script:
1. Scans existing .meta.json files from the old structure
2. Maps old categories to JD areas/categories
3. Creates ID folders grouped by correspondent + year
4. Copies files to new JD structure
5. Generates JDex index (00.00 Index.md)

Usage:
    python migrate_to_jd.py --source ./organized --dest ./jd_documents
    python migrate_to_jd.py --source ./organized --dest ./jd_documents --dry-run
"""

import os
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ==============================================================================
# JOHNNY.DECIMAL STRUCTURE
# ==============================================================================

JD_AREAS = {
    "00-09 System": {
        "00 Index": [],
        "01 Inbox": [],
        "02 Templates": [],
    },
    "10-19 Finance": {
        "11 Banking": ["bank_statements", "financial_statements"],
        "12 Taxes": ["tax_documents"],
        "13 Insurance": ["insurance"],
        "14 Receipts": ["receipts"],
        "15 Investments": [],
        "16 Bills": ["invoices"],
    },
    "20-29 Medical": {
        "21 Records": ["records", "lab_results", "appointments"],
        "22 Insurance": ["insurance"],
        "23 Prescriptions": ["prescriptions"],
        "24 Dental": [],
        "25 Vision": [],
    },
    "30-39 Legal": {
        "31 Contracts": ["contracts", "agreements", "correspondence", "court"],
        "32 Property": ["property"],
        "33 Identity": ["identification"],
        "34 Warranties": [],
    },
    "40-49 Work": {
        "41 Employment": ["hr", "correspondence"],
        "42 Expenses": [],
        "43 Projects": ["projects", "reports", "documentation"],
        "44 Certifications": [],
    },
    "50-59 Personal": {
        "51 Education": ["certificates", "assignments", "notes", "transcripts"],
        "52 Travel": [],
        "53 Certificates": [],
        "54 Memberships": ["correspondence", "miscellaneous"],
    },
    "90-99 Archive": {
        "91 2024": [],
        "92 2023": [],
    },
}

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
    ("education", "certificates"): ("50-59 Personal", "51 Education"),
    ("education", "assignments"): ("50-59 Personal", "51 Education"),
    ("education", "notes"): ("50-59 Personal", "51 Education"),
    ("education", "agreements"): ("50-59 Personal", "51 Education"),
    ("education", "transcripts"): ("50-59 Personal", "51 Education"),
    ("other", "miscellaneous"): ("50-59 Personal", "54 Memberships"),
}


def get_jd_mapping(category: str, subcategory: str) -> tuple:
    """Map old category/subcategory to JD area/category."""
    key = (category.lower(), subcategory.lower())
    if key in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[key]
    # Default fallback
    return ("50-59 Personal", "54 Memberships")


def extract_correspondent(metadata: dict) -> str:
    """Extract correspondent/source from metadata."""
    entities = metadata.get("entities", [])
    if entities:
        # Use first entity as correspondent
        return entities[0].replace(" ", "_").replace("/", "_")[:30]

    # Fallback: try to extract from original filename
    original = metadata.get("original_filename", "")
    if original:
        stem = Path(original).stem
        # Remove date prefix if present
        parts = stem.split("_")
        if len(parts) > 1 and parts[0].isdigit():
            return "_".join(parts[1:])[:30]
        return stem[:30]

    return "Unknown"


def extract_year(metadata: dict) -> str:
    """Extract year from metadata."""
    date_mentioned = metadata.get("date_mentioned")
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


def scan_existing_files(source_dir: str) -> list:
    """Scan all .meta.json files and return file info."""
    files = []
    source_path = Path(source_dir)

    for meta_path in source_path.rglob("*.meta.json"):
        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            # Find the actual document file
            doc_path = Path(str(meta_path).replace(".meta.json", ""))
            if not doc_path.exists():
                # Try without double extension
                doc_name = meta_path.stem.replace(".meta", "")
                doc_path = meta_path.parent / doc_name

            if not doc_path.exists():
                print(f"  Warning: Document not found for {meta_path}")
                continue

            files.append({
                "doc_path": doc_path,
                "meta_path": meta_path,
                "metadata": metadata,
            })
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Error reading {meta_path}: {e}")

    return files


def create_jd_folder_structure(dest_dir: str):
    """Create the base JD folder structure."""
    dest_path = Path(dest_dir)

    for area, categories in JD_AREAS.items():
        area_path = dest_path / area
        area_path.mkdir(parents=True, exist_ok=True)

        for category in categories:
            cat_path = area_path / category
            cat_path.mkdir(exist_ok=True)


def migrate_files(source_dir: str, dest_dir: str, dry_run: bool = False) -> dict:
    """Migrate files from old structure to JD structure."""
    print(f"\nScanning source directory: {source_dir}")
    files = scan_existing_files(source_dir)
    print(f"Found {len(files)} files to migrate\n")

    if not files:
        return {"migrated": 0, "errors": 0, "index_entries": []}

    # Create base structure
    if not dry_run:
        create_jd_folder_structure(dest_dir)

    # Track IDs per category
    id_tracker = defaultdict(lambda: defaultdict(int))  # category -> correspondent_year -> count
    index_entries = []
    migrated = 0
    errors = 0

    # Group files by JD category and correspondent+year
    grouped = defaultdict(list)

    for file_info in files:
        metadata = file_info["metadata"]
        old_category = metadata.get("category", "other")
        old_subcategory = metadata.get("subcategory", "miscellaneous")

        jd_area, jd_category = get_jd_mapping(old_category, old_subcategory)
        correspondent = extract_correspondent(metadata)
        year = extract_year(metadata)

        group_key = (jd_area, jd_category, correspondent, year)
        grouped[group_key].append(file_info)

    # Process each group
    for (jd_area, jd_category, correspondent, year), group_files in grouped.items():
        # Get category number (e.g., "14" from "14 Receipts")
        cat_num = jd_category.split()[0]

        # Assign ID for this correspondent+year
        id_key = f"{correspondent}_{year}"
        id_tracker[jd_category][id_key] += 1
        id_num = len(id_tracker[jd_category])

        jd_id = f"{cat_num}.{id_num:02d}"
        id_folder_name = f"{jd_id} {correspondent} {year}"

        # Create ID folder path
        id_folder_path = Path(dest_dir) / jd_area / jd_category / id_folder_name

        if not dry_run:
            id_folder_path.mkdir(parents=True, exist_ok=True)

        print(f"\n{id_folder_name}/ ({len(group_files)} files)")

        for file_info in group_files:
            doc_path = file_info["doc_path"]
            meta_path = file_info["meta_path"]
            metadata = file_info["metadata"]

            # Destination paths
            new_doc_path = id_folder_path / doc_path.name
            new_meta_path = id_folder_path / meta_path.name

            # Update metadata with JD fields
            updated_metadata = {
                **metadata,
                "id": jd_id,
                "jd_area": jd_area,
                "jd_category": jd_category,
                "correspondent": correspondent,
                "current_filename": doc_path.name,
            }

            try:
                if dry_run:
                    print(f"  [DRY RUN] Would copy: {doc_path.name}")
                else:
                    # Copy document
                    shutil.copy2(doc_path, new_doc_path)

                    # Write updated metadata
                    with open(new_meta_path, 'w') as f:
                        json.dump(updated_metadata, f, indent=2, ensure_ascii=False)

                    print(f"  Copied: {doc_path.name}")

                # Add to index
                index_entries.append({
                    "id": jd_id,
                    "jd_area": jd_area,
                    "jd_category": jd_category,
                    "correspondent": correspondent,
                    "year": year,
                    "filename": doc_path.name,
                    "summary": metadata.get("summary", ""),
                    "tags": metadata.get("tags", []),
                    "date_mentioned": metadata.get("date_mentioned"),
                })

                migrated += 1

            except Exception as e:
                print(f"  Error copying {doc_path.name}: {e}")
                errors += 1

    return {
        "migrated": migrated,
        "errors": errors,
        "index_entries": index_entries,
    }


def generate_jdex_index(dest_dir: str, index_entries: list, dry_run: bool = False):
    """Generate the JDex index file (00.00 Index.md)."""
    index_path = Path(dest_dir) / "00-09 System" / "00 Index" / "00.00 Index.md"

    # Group entries by area and category
    grouped = defaultdict(lambda: defaultdict(list))
    for entry in index_entries:
        grouped[entry["jd_area"]][entry["jd_category"]].append(entry)

    # Generate markdown
    lines = [
        "# JDex Index",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Total documents: {len(index_entries)}",
        "",
        "---",
        "",
    ]

    # Sort by area and category
    for area in sorted(grouped.keys()):
        lines.append(f"## {area}")
        lines.append("")

        for category in sorted(grouped[area].keys()):
            entries = grouped[area][category]
            lines.append(f"### {category}")
            lines.append("")

            # Group by ID
            by_id = defaultdict(list)
            for entry in entries:
                by_id[entry["id"]].append(entry)

            for jd_id in sorted(by_id.keys()):
                id_entries = by_id[jd_id]
                first = id_entries[0]
                lines.append(f"#### {jd_id} {first['correspondent']} {first['year']}")
                lines.append(f"Location: file system")
                lines.append("")

                for entry in id_entries:
                    summary = entry.get("summary", "")[:100]
                    if len(entry.get("summary", "")) > 100:
                        summary += "..."
                    lines.append(f"- {entry['filename']}")
                    if summary:
                        lines.append(f"  {summary}")

                lines.append("")

        lines.append("")

    content = "\n".join(lines)

    if dry_run:
        print("\n[DRY RUN] Would create JDex index:")
        print(content[:1000] + "..." if len(content) > 1000 else content)
    else:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, 'w') as f:
            f.write(content)
        print(f"\nJDex index created: {index_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate documents to Johnny.Decimal structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--source", "-s",
        default="/Users/batch/Documents/scanned_documents/organized",
        help="Source directory with existing organized files"
    )
    parser.add_argument(
        "--dest", "-d",
        default="/Users/batch/Documents/scanned_documents/jd_documents",
        help="Destination directory for JD structure"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Johnny.Decimal Migration")
    print("=" * 60)
    print(f"Source: {args.source}")
    print(f"Destination: {args.dest}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print("=" * 60)

    result = migrate_files(args.source, args.dest, args.dry_run)

    print("\n" + "=" * 60)
    print(f"Migration complete!")
    print(f"  Migrated: {result['migrated']} files")
    print(f"  Errors: {result['errors']}")
    print("=" * 60)

    if result["index_entries"]:
        generate_jdex_index(args.dest, result["index_entries"], args.dry_run)


if __name__ == "__main__":
    main()
