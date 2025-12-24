#!/usr/bin/env python3
"""
Preview Renames - Generate a report of proposed folder/file renames.

This script scans existing jd_documents and proposes new names based on
the improved naming convention (Issuer + Document Type instead of correspondent).

Usage:
    # Preview mode (default) - just show what would be renamed
    python preview_renames.py

    # Generate markdown report
    python preview_renames.py --output renames_report.md

    # Re-analyze documents with AI (slower but more accurate)
    python preview_renames.py --reanalyze
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from document_organizer import (
    JD_AREAS,
    generate_folder_descriptor,
    slugify,
    extract_text_with_docling,
    extract_text_fallback,
    categorize_with_claude_code,
)

# Default JD documents path
DEFAULT_JD_PATH = "/Users/batch/Documents/scanned_documents/jd_documents"


def load_metadata(folder_path: Path) -> Optional[dict]:
    """Load metadata from .meta.json files in a folder."""
    for f in folder_path.iterdir():
        if f.suffix == ".json" and ".meta.json" in f.name:
            try:
                with open(f, 'r') as fp:
                    return json.load(fp)
            except (json.JSONDecodeError, IOError):
                continue
    return None


def extract_current_info(folder_name: str) -> dict:
    """Extract JD ID, current descriptor, and year from folder name."""
    # Format: "14.01 Some_Descriptor 2024"
    parts = folder_name.split(" ", 1)
    if len(parts) < 2:
        return {"jd_id": parts[0] if parts else "", "descriptor": "", "year": ""}

    jd_id = parts[0]
    rest = parts[1]

    # Try to extract year from end
    rest_parts = rest.rsplit(" ", 1)
    if len(rest_parts) == 2 and rest_parts[1].isdigit() and len(rest_parts[1]) == 4:
        descriptor = rest_parts[0]
        year = rest_parts[1]
    else:
        descriptor = rest
        year = ""

    return {"jd_id": jd_id, "descriptor": descriptor, "year": year}


def propose_new_name_from_ai(metadata: dict, folder_name: str) -> Optional[str]:
    """Use Claude Code to propose a better name based on existing metadata."""
    import subprocess
    import json as json_module

    summary = metadata.get("summary", "")
    extracted_text = metadata.get("extracted_text", "")
    existing_tags = metadata.get("tags", [])
    correspondent = metadata.get("correspondent", "")

    # Build context from metadata
    context = f"""Summary: {summary}
Tags: {', '.join(existing_tags) if existing_tags else 'none'}
Current folder name: {folder_name}
Correspondent (old field): {correspondent}"""

    # Add a snippet of extracted text if available
    if extracted_text:
        context += f"\n\nExtracted text (first 1500 chars):\n{extracted_text[:1500]}"

    prompt = f"""Based on this document metadata, suggest a proper folder name.

{context}

RULES:
- "issuer" = organization that CREATED/ISSUED the document (hospital, company, government office)
- "document_type" = WHAT the document IS (Blood Test Results, Employment Contract, Invoice)
- Do NOT use personal names like "Batyr Charyyev" as the issuer
- Personal names are only valid if they're a business (e.g., "Dr. Marcus Maurer" for a doctor's practice)

Respond with ONLY valid JSON:
{{"issuer": "organization name", "document_type": "type of document"}}"""

    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        result_text = result.stdout.strip()

        # Parse JSON from response
        import re
        json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
        if json_match:
            data = json_module.loads(json_match.group())
            issuer = data.get("issuer", "")
            doc_type = data.get("document_type", "")
            if issuer and doc_type:
                return f"{issuer} {doc_type}"
            elif doc_type:
                return doc_type
            elif issuer:
                return issuer
        return None
    except Exception as e:
        print(f"    ⚠️ AI analysis failed: {e}")
        return None


def propose_new_name(metadata: dict, original_name: str) -> str:
    """Generate proposed new folder descriptor from metadata (fallback without AI)."""
    # Try new fields first
    issuer = metadata.get("issuer", "")
    document_type = metadata.get("document_type", "")

    if issuer and document_type:
        return f"{issuer} {document_type}"
    elif document_type:
        return document_type
    elif issuer:
        return issuer

    # Fall back to summary if available
    summary = metadata.get("summary", "")
    if summary and len(summary) > 5:
        # Extract first few meaningful words
        words = summary.split()[:4]
        return " ".join(words).title()

    # Last resort: clean up original
    return original_name.replace("_", " ").title()


def scan_jd_documents(jd_path: str, reanalyze: bool = False, mode: str = "api") -> list:
    """Scan JD documents and generate rename proposals."""
    proposals = []
    jd_root = Path(jd_path)

    # Walk through Area > Category > ID Folder structure
    for area_dir in sorted(jd_root.iterdir()):
        if not area_dir.is_dir() or area_dir.name.startswith("."):
            continue

        for category_dir in sorted(area_dir.iterdir()):
            if not category_dir.is_dir() or category_dir.name.startswith("."):
                continue

            for id_folder in sorted(category_dir.iterdir()):
                if not id_folder.is_dir() or id_folder.name.startswith("."):
                    continue

                current_info = extract_current_info(id_folder.name)
                metadata = load_metadata(id_folder)

                # Check if this needs renaming
                current_descriptor = current_info["descriptor"]

                # Skip if already has good naming (issuer + document_type pattern)
                if metadata and metadata.get("issuer") and metadata.get("document_type"):
                    proposed = f"{metadata['issuer']} {metadata['document_type']}"
                    if current_descriptor == proposed:
                        continue  # Already good

                # Get proposed name
                if reanalyze:
                    print(f"  Analyzing: {id_folder.name}...")

                    if metadata:
                        # Use AI to analyze existing metadata (fast path)
                        proposed_descriptor = propose_new_name_from_ai(metadata, id_folder.name)
                    else:
                        # No metadata - need to extract text from document first
                        proposed_descriptor = None
                        doc_files = [f for f in id_folder.iterdir()
                                    if f.is_file() and f.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg']]
                        if doc_files:
                            print(f"    No metadata found, extracting from {doc_files[0].name}...")
                            result = extract_text_with_docling(str(doc_files[0]))
                            if not result["success"]:
                                result = extract_text_fallback(str(doc_files[0]))

                            if result["success"] and result["text"]:
                                # Create a fake metadata dict from extracted text
                                fake_metadata = {
                                    "extracted_text": result["text"],
                                    "summary": result["text"][:500]
                                }
                                proposed_descriptor = propose_new_name_from_ai(fake_metadata, id_folder.name)

                    if not proposed_descriptor:
                        # Fallback if AI fails
                        proposed_descriptor = propose_new_name(metadata or {}, current_descriptor)
                else:
                    # Use existing metadata without AI
                    proposed_descriptor = propose_new_name(metadata or {}, current_descriptor)

                # Generate proposed folder name
                jd_id = current_info["jd_id"]
                year = current_info["year"] or str(datetime.now().year)
                proposed_folder = f"{jd_id} {proposed_descriptor} {year}"

                # Only add if different
                if proposed_folder != id_folder.name:
                    proposals.append({
                        "area": area_dir.name,
                        "category": category_dir.name,
                        "current_path": str(id_folder),
                        "current_name": id_folder.name,
                        "proposed_name": proposed_folder,
                        "reason": detect_issue(current_descriptor, metadata),
                    })

    return proposals


def detect_issue(descriptor: str, metadata: Optional[dict]) -> str:
    """Detect why this folder needs renaming."""
    descriptor_lower = descriptor.lower()

    # Check for personal name patterns
    personal_names = ["batyr", "charyyev", "porsyyeva", "aygul"]
    for name in personal_names:
        if name in descriptor_lower:
            return "Uses personal name instead of document type"

    # Check for vague descriptors
    if len(descriptor) < 5:
        return "Descriptor too short/vague"

    # Check for URL fragments
    if "http" in descriptor_lower or "://" in descriptor_lower:
        return "Contains URL fragment"

    # Check for file extensions in name
    if any(ext in descriptor_lower for ext in [".pdf", ".docx", ".png"]):
        return "Contains file extension"

    return "Missing issuer/document type"


def execute_renames(proposals: list, dry_run: bool = False) -> dict:
    """Execute the proposed folder renames."""
    results = {"success": [], "failed": []}

    for p in proposals:
        old_path = Path(p["current_path"])
        new_path = old_path.parent / p["proposed_name"]

        if dry_run:
            print(f"  [DRY RUN] {old_path.name} → {new_path.name}")
            results["success"].append(p)
            continue

        try:
            old_path.rename(new_path)
            print(f"  ✓ {old_path.name} → {new_path.name}")
            results["success"].append(p)
        except Exception as e:
            print(f"  ✗ {old_path.name}: {e}")
            results["failed"].append({**p, "error": str(e)})

    return results


def generate_report(proposals: list, output_path: Optional[str] = None) -> str:
    """Generate a markdown report of proposed renames."""
    lines = [
        "# Document Rename Proposals",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Total folders to rename: **{len(proposals)}**",
        "",
        "---",
        "",
    ]

    # Group by category
    by_category = {}
    for p in proposals:
        key = f"{p['area']} / {p['category']}"
        if key not in by_category:
            by_category[key] = []
        by_category[key].append(p)

    for category, items in sorted(by_category.items()):
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| Current | Proposed | Issue |")
        lines.append("|---------|----------|-------|")

        for item in items:
            current = item['current_name']
            proposed = item['proposed_name']
            reason = item.get('reason', '')
            lines.append(f"| `{current}` | `{proposed}` | {reason} |")

        lines.append("")

    report = "\n".join(lines)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"Report saved to: {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Preview document folder renames based on improved naming convention"
    )
    parser.add_argument(
        "--jd-path",
        default=DEFAULT_JD_PATH,
        help="Path to jd_documents folder"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file for markdown report"
    )
    parser.add_argument(
        "--reanalyze",
        action="store_true",
        help="Re-analyze documents with AI (slower but more accurate)"
    )
    parser.add_argument(
        "--mode",
        choices=["api", "claude-code"],
        default="claude-code",
        help="AI mode for reanalysis (default: claude-code)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the renames (default: preview only)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be renamed without actually doing it"
    )

    args = parser.parse_args()

    print(f"Scanning: {args.jd_path}")
    print(f"Reanalyze mode: {'ON' if args.reanalyze else 'OFF'}")
    print()

    proposals = scan_jd_documents(args.jd_path, args.reanalyze, args.mode)

    if not proposals:
        print("No folders need renaming!")
        return

    if args.execute:
        # Execute mode - actually rename the folders
        mode_str = "[DRY RUN] " if args.dry_run else ""
        print(f"\n{mode_str}Executing {len(proposals)} renames...")
        results = execute_renames(proposals, dry_run=args.dry_run)
        print(f"\n{mode_str}Renamed: {len(results['success'])}")
        if results["failed"]:
            print(f"Failed: {len(results['failed'])}")
            for f in results["failed"]:
                print(f"  - {f['current_name']}: {f.get('error', 'unknown error')}")
    else:
        # Preview mode - generate report
        report = generate_report(proposals, args.output)

        if not args.output:
            print(report)

        print(f"\nFound {len(proposals)} folders that could be renamed.")
        print("Run with --execute to perform the renames.")
        print("Run with --execute --dry-run to preview what would happen.")


if __name__ == "__main__":
    main()
