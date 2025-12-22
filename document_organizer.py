#!/usr/bin/env python3
"""
Document Organizer - Automatically organize scanned documents using Docling + AI

This script watches an inbox folder and automatically:
1. Extracts text from documents using Docling
2. Uses an LLM to analyze and categorize the content
3. Moves files to organized folder structures with metadata tags

Usage:
    python document_organizer.py --inbox ./inbox --output ./organized
    
Or run once (no watching):
    python document_organizer.py --inbox ./inbox --output ./organized --once
"""

import os
import sys
import json
import shutil
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
import time

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Default categories - customize these for your needs!
DEFAULT_CATEGORIES = {
    "financial": {
        "subcategories": ["invoices", "receipts", "tax_documents", "bank_statements", "contracts"],
        "keywords": ["invoice", "receipt", "tax", "payment", "bank", "statement", "account"]
    },
    "medical": {
        "subcategories": ["prescriptions", "lab_results", "insurance", "appointments", "records"],
        "keywords": ["medical", "doctor", "patient", "diagnosis", "prescription", "health", "hospital"]
    },
    "legal": {
        "subcategories": ["contracts", "agreements", "correspondence", "court", "property"],
        "keywords": ["agreement", "contract", "legal", "attorney", "court", "law", "hereby"]
    },
    "personal": {
        "subcategories": ["identification", "correspondence", "certificates", "photos"],
        "keywords": ["passport", "license", "certificate", "birth", "marriage", "id"]
    },
    "work": {
        "subcategories": ["reports", "presentations", "correspondence", "projects", "hr"],
        "keywords": ["report", "meeting", "project", "employee", "company", "quarterly"]
    },
    "education": {
        "subcategories": ["transcripts", "certificates", "assignments", "notes"],
        "keywords": ["school", "university", "grade", "course", "student", "degree", "diploma"]
    },
    "other": {
        "subcategories": ["miscellaneous"],
        "keywords": []
    }
}

# ==============================================================================
# DOCUMENT PROCESSING
# ==============================================================================

def extract_text_with_docling(file_path: str) -> dict:
    """Extract text and metadata from a document using Docling."""
    try:
        from docling.document_converter import DocumentConverter
        
        converter = DocumentConverter()
        result = converter.convert(file_path)
        
        # Get the full text
        text = result.document.export_to_markdown()
        
        # Try to get any metadata
        metadata = {
            "pages": len(result.document.pages) if hasattr(result.document, 'pages') else None,
            "format": Path(file_path).suffix.lower(),
        }
        
        return {
            "success": True,
            "text": text,
            "metadata": metadata
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "metadata": {}
        }


def extract_text_fallback(file_path: str) -> dict:
    """Fallback text extraction using simpler methods."""
    suffix = Path(file_path).suffix.lower()
    
    try:
        if suffix == '.pdf':
            # Try pdfplumber
            import pdfplumber
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return {"success": True, "text": text, "metadata": {"pages": len(pdf.pages)}}
        
        elif suffix == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return {"success": True, "text": f.read(), "metadata": {}}
        
        elif suffix in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            # OCR for images
            import pytesseract
            from PIL import Image
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            return {"success": True, "text": text, "metadata": {"type": "image"}}
        
        else:
            return {"success": False, "text": "", "error": f"Unsupported format: {suffix}"}
            
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}


# ==============================================================================
# AI CATEGORIZATION
# ==============================================================================

def categorize_with_keywords(text: str, categories: dict) -> dict:
    """Simple keyword-based categorization (no API needed)."""
    text_lower = text.lower()
    scores = {}
    
    for category, config in categories.items():
        score = sum(1 for kw in config["keywords"] if kw in text_lower)
        scores[category] = score
    
    # Find best category
    best_category = max(scores, key=scores.get) if max(scores.values()) > 0 else "other"
    
    # Simple tag extraction - find matching keywords
    tags = []
    for category, config in categories.items():
        for kw in config["keywords"]:
            if kw in text_lower and kw not in tags:
                tags.append(kw)
    
    return {
        "category": best_category,
        "subcategory": categories[best_category]["subcategories"][0],
        "tags": tags[:10],  # Limit to 10 tags
        "confidence": "low",
        "summary": text[:200] + "..." if len(text) > 200 else text
    }


def categorize_with_claude_code(text: str, categories: dict) -> dict:
    """Use Claude Code CLI (works with Max subscription) to categorize."""
    import subprocess
    
    # Truncate text if too long
    max_chars = 6000
    truncated_text = text[:max_chars] if len(text) > max_chars else text
    
    category_list = list(categories.keys())
    
    prompt = f"""Analyze this document and categorize it. 

Available categories: {', '.join(category_list)}

For each category, these are the subcategories:
{json.dumps({k: v['subcategories'] for k, v in categories.items()}, indent=2)}

Document content:
---
{truncated_text}
---

Respond with ONLY valid JSON in this exact format (no other text):
{{"category": "one of the categories", "subcategory": "subcategory", "tags": ["tag1", "tag2"], "confidence": "high/medium/low", "summary": "One sentence summary", "date_mentioned": "YYYY-MM-DD or null", "entities": ["names"]}}"""

    try:
        # Use Claude Code CLI with --print flag for non-interactive output
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise Exception(f"Claude Code failed: {result.stderr}")
        
        result_text = result.stdout.strip()
        
        # Parse JSON from response
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        # Try to find JSON in the response
        import re
        json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group()
            
        return json.loads(result_text)
        
    except FileNotFoundError:
        print("  ⚠️  Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return None
    except Exception as e:
        print(f"  ⚠️  Claude Code categorization failed: {e}")
        return None


def categorize_with_llm(text: str, categories: dict, api_key: Optional[str] = None) -> dict:
    """Use Claude API to intelligently categorize the document."""
    
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("  ⚠️  No API key found, using keyword-based categorization")
        return categorize_with_keywords(text, categories)
    
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Truncate text if too long
        max_chars = 8000
        truncated_text = text[:max_chars] if len(text) > max_chars else text
        
        category_list = list(categories.keys())
        
        prompt = f"""Analyze this document and categorize it. 

Available categories: {', '.join(category_list)}

For each category, these are the subcategories:
{json.dumps({k: v['subcategories'] for k, v in categories.items()}, indent=2)}

Document content:
---
{truncated_text}
---

Respond with ONLY valid JSON in this exact format:
{{
    "category": "one of the categories listed above",
    "subcategory": "one of the subcategories for that category",
    "tags": ["tag1", "tag2", "tag3"],
    "confidence": "high/medium/low",
    "summary": "One sentence summary of the document",
    "date_mentioned": "YYYY-MM-DD if a date is found, null otherwise",
    "entities": ["person names", "company names", "etc"]
}}"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text.strip()
        
        # Parse JSON from response
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
            
        return json.loads(result_text)
        
    except Exception as e:
        print(f"  ⚠️  LLM categorization failed: {e}")
        return categorize_with_keywords(text, categories)


# ==============================================================================
# FILE ORGANIZATION
# ==============================================================================

def generate_filename(original_name: str, analysis: dict) -> str:
    """Generate a descriptive filename based on analysis."""
    suffix = Path(original_name).suffix
    
    # Use date if found
    date_part = analysis.get("date_mentioned", "")
    if date_part:
        date_part = date_part.replace("-", "") + "_"
    else:
        date_part = datetime.now().strftime("%Y%m%d") + "_"
    
    # Use first entity or first tag for naming
    entities = analysis.get("entities", [])
    tags = analysis.get("tags", [])
    
    name_part = ""
    if entities:
        name_part = entities[0].replace(" ", "_")[:30]
    elif tags:
        name_part = "_".join(tags[:2])[:30]
    else:
        name_part = Path(original_name).stem[:30]
    
    # Clean the name
    name_part = "".join(c if c.isalnum() or c == "_" else "_" for c in name_part)
    
    return f"{date_part}{name_part}{suffix}"


def create_metadata_file(file_path: str, analysis: dict, original_name: str, extracted_text: str = ""):
    """Create a JSON sidecar file with metadata and extracted text."""
    metadata = {
        "original_filename": original_name,
        "organized_date": datetime.now().isoformat(),
        "category": analysis.get("category"),
        "subcategory": analysis.get("subcategory"),
        "tags": analysis.get("tags", []),
        "summary": analysis.get("summary", ""),
        "confidence": analysis.get("confidence", ""),
        "entities": analysis.get("entities", []),
        "date_mentioned": analysis.get("date_mentioned"),
        "extracted_text": extracted_text
    }

    metadata_path = Path(file_path).with_suffix(Path(file_path).suffix + ".meta.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def organize_file(file_path: str, output_dir: str, analysis: dict, extracted_text: str = "") -> str:
    """Move file to organized folder structure."""
    category = analysis.get("category", "other")
    subcategory = analysis.get("subcategory", "miscellaneous")

    # Create folder structure: output/category/subcategory/
    dest_dir = Path(output_dir) / category / subcategory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Generate new filename
    new_name = generate_filename(Path(file_path).name, analysis)
    dest_path = dest_dir / new_name

    # Handle duplicates
    counter = 1
    while dest_path.exists():
        stem = Path(new_name).stem
        suffix = Path(new_name).suffix
        dest_path = dest_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    original_name = Path(file_path).name

    # Move the file
    shutil.move(file_path, dest_path)

    # Create metadata sidecar with extracted text
    create_metadata_file(str(dest_path), analysis, original_name, extracted_text)

    # Add to central search index
    add_to_search_index(output_dir, str(dest_path), original_name, analysis, extracted_text)

    return str(dest_path)


# ==============================================================================
# PROCESSED FILES TRACKING
# ==============================================================================

def get_processed_db_path(output_dir: str) -> Path:
    """Get path to the processed files database."""
    return Path(output_dir) / ".processed_files.json"


def load_processed_files(output_dir: str) -> dict:
    """Load the processed files database from JSON."""
    db_path = get_processed_db_path(output_dir)
    if db_path.exists():
        try:
            with open(db_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_processed_files(output_dir: str, processed: dict):
    """Save the processed files database to JSON."""
    db_path = get_processed_db_path(output_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with open(db_path, 'w') as f:
        json.dump(processed, f, indent=2)


# ==============================================================================
# SEARCH INDEX
# ==============================================================================

def get_search_index_path(output_dir: str) -> Path:
    """Get path to the search index file."""
    return Path(output_dir) / ".search_index.json"


def load_search_index(output_dir: str) -> list:
    """Load the search index from JSON."""
    index_path = get_search_index_path(output_dir)
    if index_path.exists():
        try:
            with open(index_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_search_index(output_dir: str, index: list):
    """Save the search index to JSON."""
    index_path = get_search_index_path(output_dir)
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def add_to_search_index(output_dir: str, doc_path: str, original_name: str,
                        analysis: dict, extracted_text: str):
    """Add a document to the search index."""
    index = load_search_index(output_dir)

    entry = {
        "file_path": doc_path,
        "original_filename": original_name,
        "category": analysis.get("category"),
        "subcategory": analysis.get("subcategory"),
        "tags": analysis.get("tags", []),
        "summary": analysis.get("summary", ""),
        "entities": analysis.get("entities", []),
        "date_mentioned": analysis.get("date_mentioned"),
        "indexed_at": datetime.now().isoformat(),
        "extracted_text": extracted_text
    }

    index.append(entry)
    save_search_index(output_dir, index)


def get_file_hash(file_path: str) -> str:
    """Generate a hash based on file content."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_file_processed(file_path: str, processed: dict) -> bool:
    """Check if a file has already been processed (by content hash)."""
    file_hash = get_file_hash(file_path)
    return file_hash in processed


def mark_file_processed(file_hash: str, original_name: str, dest_path: str, processed: dict):
    """Mark a file as processed in the database."""
    processed[file_hash] = {
        "original_name": original_name,
        "destination": dest_path,
        "processed_at": datetime.now().isoformat()
    }


# ==============================================================================
# MAIN PROCESSING
# ==============================================================================

def process_file(file_path: str, output_dir: str, categories: dict, mode: str = "claude-code") -> dict:
    """Process a single file: extract, categorize, organize.
    
    mode: "claude-code" (uses Max subscription), "api" (uses ANTHROPIC_API_KEY), "keywords" (no AI)
    """
    print(f"\n📄 Processing: {Path(file_path).name}")
    
    # Step 1: Extract text
    print("  📖 Extracting text...")
    result = extract_text_with_docling(file_path)
    
    if not result["success"]:
        print(f"  ⚠️  Docling failed, trying fallback: {result.get('error', 'unknown')}")
        result = extract_text_fallback(file_path)
    
    if not result["success"] or not result["text"].strip():
        print(f"  ❌ Could not extract text from file")
        # Move to 'failed' folder
        failed_dir = Path(output_dir) / "_failed"
        failed_dir.mkdir(exist_ok=True)
        dest = failed_dir / Path(file_path).name
        shutil.move(file_path, dest)
        return {"success": False, "error": "Text extraction failed"}
    
    print(f"  ✅ Extracted {len(result['text'])} characters")
    
    # Step 2: Categorize
    print("  🤖 Analyzing content...")
    analysis = None
    
    if mode == "claude-code":
        analysis = categorize_with_claude_code(result["text"], categories)
        if analysis is None:
            print("  ⚠️  Falling back to keyword matching")
            analysis = categorize_with_keywords(result["text"], categories)
    elif mode == "api":
        analysis = categorize_with_llm(result["text"], categories)
    else:
        analysis = categorize_with_keywords(result["text"], categories)
    
    print(f"  📁 Category: {analysis['category']}/{analysis['subcategory']}")
    print(f"  🏷️  Tags: {', '.join(analysis.get('tags', [])[:5])}")

    # Step 3: Organize (pass extracted text for searchable index)
    print("  📦 Organizing...")
    extracted_text = result["text"]
    dest_path = organize_file(file_path, output_dir, analysis, extracted_text)
    print(f"  ✅ Moved to: {dest_path}")
    
    return {
        "success": True,
        "original": file_path,
        "destination": dest_path,
        "analysis": analysis
    }


def watch_folder(inbox_dir: str, output_dir: str, categories: dict, mode: str = "claude-code", interval: int = 5):
    """Watch inbox folder and process new files."""
    print(f"\n👁️  Watching folder: {inbox_dir}")
    print(f"📤 Output folder: {output_dir}")
    print(f"🤖 Mode: {mode}")
    print(f"🔄 Checking every {interval} seconds (Ctrl+C to stop)\n")

    # Load persistent processed files database
    processed = load_processed_files(output_dir)
    print(f"📋 Loaded {len(processed)} previously processed files from database\n")

    supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.docx', '.pptx', '.xlsx', '.txt', '.html'}

    while True:
        try:
            inbox = Path(inbox_dir)

            for file_path in inbox.iterdir():
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() not in supported_extensions:
                    continue

                # Get file hash before processing (file will be moved)
                file_hash = get_file_hash(str(file_path))
                original_name = file_path.name

                # Skip already processed files (by content hash)
                if file_hash in processed:
                    print(f"⏭️  Skipping duplicate: {file_path.name}")
                    # Remove the duplicate from inbox
                    file_path.unlink()
                    continue

                # Process the file
                result = process_file(str(file_path), output_dir, categories, mode)

                if result.get("success"):
                    mark_file_processed(file_hash, original_name, result["destination"], processed)
                    save_processed_files(output_dir, processed)

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n👋 Stopping watcher...")
            break


def process_once(inbox_dir: str, output_dir: str, categories: dict, mode: str = "claude-code"):
    """Process all files in inbox once (no watching)."""
    print(f"\n📥 Processing all files in: {inbox_dir}")
    print(f"📤 Output folder: {output_dir}")
    print(f"🤖 Mode: {mode}\n")

    # Load persistent processed files database
    processed = load_processed_files(output_dir)
    print(f"📋 Loaded {len(processed)} previously processed files from database\n")

    supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.docx', '.pptx', '.xlsx', '.txt', '.html'}
    inbox = Path(inbox_dir)

    results = []
    skipped = 0
    for file_path in inbox.iterdir():
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in supported_extensions:
            continue

        # Get file hash before processing (file will be moved)
        file_hash = get_file_hash(str(file_path))
        original_name = file_path.name

        # Skip already processed files (by content hash)
        if file_hash in processed:
            print(f"⏭️  Skipping duplicate: {file_path.name}")
            file_path.unlink()  # Remove the duplicate from inbox
            skipped += 1
            continue

        result = process_file(str(file_path), output_dir, categories, mode)
        results.append(result)

        if result.get("success"):
            mark_file_processed(file_hash, original_name, result["destination"], processed)

    # Save updated database
    save_processed_files(output_dir, processed)

    # Summary
    successful = sum(1 for r in results if r.get("success"))
    print(f"\n{'='*50}")
    print(f"✅ Processed {successful}/{len(results)} files successfully")
    if skipped:
        print(f"⏭️  Skipped {skipped} duplicate files")

    return results


# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Automatically organize documents using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use Claude Code with your Max subscription (recommended)
  python document_organizer.py --inbox ./inbox --output ./organized
  
  # Use API key instead
  python document_organizer.py --inbox ./inbox --output ./organized --mode api
  
  # Use only keyword matching (no AI needed)
  python document_organizer.py --inbox ./inbox --output ./organized --mode keywords
  
  # Process all files once (don't watch)
  python document_organizer.py --inbox ./inbox --output ./organized --once

Modes:
  claude-code  Use Claude Code CLI (works with Max subscription, no API key needed)
  api          Use Anthropic API (requires ANTHROPIC_API_KEY env variable)
  keywords     Simple keyword matching (no AI, always works)
        """
    )
    
    parser.add_argument("--inbox", "-i", default=os.getenv("INBOX_DIR"), help="Input folder to watch/process")
    parser.add_argument("--output", "-o", default=os.getenv("OUTPUT_DIR"), help="Output folder for organized files")
    parser.add_argument("--once", action="store_true", help="Process once and exit (don't watch)")
    parser.add_argument("--mode", "-m", choices=["claude-code", "api", "keywords"], 
                        default="claude-code", help="Categorization mode (default: claude-code)")
    parser.add_argument("--interval", type=int, default=5, help="Watch interval in seconds (default: 5)")
    
    # Legacy flag for backwards compatibility
    parser.add_argument("--no-llm", action="store_true", help="(deprecated) Use --mode keywords instead")
    
    args = parser.parse_args()
    
    # Handle legacy flag
    mode = args.mode
    if args.no_llm:
        mode = "keywords"

    # Validate required paths
    if not args.inbox:
        parser.error("--inbox is required (or set INBOX_DIR in .env)")
    if not args.output:
        parser.error("--output is required (or set OUTPUT_DIR in .env)")

    # Create directories
    Path(args.inbox).mkdir(parents=True, exist_ok=True)
    Path(args.output).mkdir(parents=True, exist_ok=True)
    
    if args.once:
        process_once(args.inbox, args.output, DEFAULT_CATEGORIES, mode)
    else:
        watch_folder(args.inbox, args.output, DEFAULT_CATEGORIES, mode, args.interval)


if __name__ == "__main__":
    main()