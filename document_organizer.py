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
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import time

import yaml
from dotenv import load_dotenv
from PIL import Image

# Load environment variables from .env file (if it exists and is accessible)
# In bundled apps, API keys are stored in OS keychain via settings.py instead
try:
    load_dotenv()
except (PermissionError, OSError):
    pass  # .env not accessible, likely running as bundled app


# ==============================================================================
# CONFIGURATION LOADING
# ==============================================================================

def load_config() -> dict:
    """Load configuration from config.yaml, with fallbacks to environment variables."""
    config = {
        "paths": {
            "output_dir": os.getenv("OUTPUT_DIR", str(Path.home() / "Documents" / "jd_documents")),
            "inbox_dir": os.getenv("INBOX_DIR", str(Path.home() / "Documents" / "jd_documents" / "00-09 System" / "01 Inbox")),
        },
        "mode": "claude-code",
        "watch_interval": 5,
        "logging": {
            "level": "INFO",
            "file": "",
        },
    }

    # Try to load from config.yaml
    config_paths = [
        Path(__file__).parent / "config.local.yaml",  # Local overrides first
        Path(__file__).parent / "config.yaml",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    yaml_config = yaml.safe_load(f) or {}

                # Merge paths
                if "paths" in yaml_config:
                    for key, value in yaml_config["paths"].items():
                        if value:
                            # Expand ~ to home directory
                            config["paths"][key] = os.path.expanduser(value)

                # Merge other settings
                if "mode" in yaml_config:
                    config["mode"] = yaml_config["mode"]
                if "watch_interval" in yaml_config:
                    config["watch_interval"] = yaml_config["watch_interval"]
                if "logging" in yaml_config:
                    config["logging"].update(yaml_config["logging"])

                break  # Use first found config
            except Exception as e:
                print(f"Warning: Could not load {config_path}: {e}")

    return config


# Load global config
CONFIG = load_config()

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging based on environment variables."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "")

    # Create logger
    logger = logging.getLogger("document_organizer")
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Prevent duplicate handlers on reimport
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (if LOG_FILE is set)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger

# Initialize logger
logger = setup_logging()

# Set a reasonable PIL decompression limit for scanned documents
# Default is ~178MP, we allow up to 200MP for large medical scans
# This prevents decompression bomb attacks while supporting most real documents
Image.MAX_IMAGE_PIXELS = 200_000_000  # 200 megapixels (safer than 500MP)

# ==============================================================================
# CONFIGURATION - JOHNNY.DECIMAL SYSTEM
# ==============================================================================

# Supported document formats for processing
SUPPORTED_FORMATS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.docx', '.pptx', '.xlsx', '.txt', '.html'}

# Johnny.Decimal Areas and Categories
# Format: AC.ID → Area-Category.Item (e.g., 14.03 = Finance area, Receipts category, item 03)
JD_AREAS = {
    "00-09 System": {
        "00 Index": {"keywords": []},
        "01 Inbox": {"keywords": []},
        "02 Templates": {"keywords": ["template"]},
        "09 Uncategorized": {"keywords": []},
    },
    "10-19 Finance": {
        "11 Banking": {"keywords": ["bank", "account", "transfer", "statement", "balance", "sparkasse", "commerzbank"]},
        "12 Taxes": {"keywords": ["tax", "steuer", "finanzamt", "steuererklärung", "w-2", "1099"]},
        "13 Insurance": {"keywords": ["insurance", "versicherung", "policy", "premium", "coverage", "claim"]},
        "14 Receipts": {"keywords": ["receipt", "quittung", "kassenbon", "purchase", "bought", "paid"]},
        "15 Investments": {"keywords": ["investment", "stock", "portfolio", "dividend", "brokerage"]},
        "16 Housing": {"keywords": ["rent", "miete", "wohnung", "apartment", "housing", "utility", "strom", "gas", "internet"]},
    },
    "20-29 Medical": {
        "21 Records": {"keywords": ["medical", "doctor", "patient", "diagnosis", "hospital", "clinic", "arzt", "krankenhaus", "lab", "blood", "test"]},
        "22 Insurance": {"keywords": ["health insurance", "krankenversicherung", "aok", "tk", "barmer"]},
        "23 Prescriptions": {"keywords": ["prescription", "rezept", "medication", "pharmacy", "apotheke"]},
        "25 Vision": {"keywords": ["eye", "vision", "optiker", "glasses", "brille", "dental", "zahnarzt", "tooth", "dentist"]},
        "26 Bills": {"keywords": ["medical bill", "arztrechnung", "hospital bill", "healthcare cost"]},
    },
    "30-39 Legal": {
        "31 Contracts": {"keywords": ["contract", "vertrag", "agreement", "vereinbarung", "signed", "parties", "terms"]},
        "32 Property": {"keywords": ["property", "immobilie", "deed", "lease", "miete", "wohnung", "grundbuch"]},
        "33 Identity": {"keywords": ["passport", "reisepass", "id", "ausweis", "license", "führerschein", "birth", "geburt"]},
        "34 Warranties": {"keywords": ["warranty", "garantie", "guarantee"]},
    },
    "40-49 Work": {
        "41 Employment": {"keywords": ["employment", "arbeit", "job", "arbeitsvertrag", "hr", "contract"]},
        "42 Expenses": {"keywords": ["expense", "reimbursement", "spesen", "erstattung"]},
        "43 Projects": {"keywords": ["project", "projekt", "report", "bericht", "presentation", "documentation"]},
        "44 Certifications": {"keywords": ["certification", "zertifikat", "professional", "training"]},
        "45 Salary & Payments": {"keywords": ["salary", "gehalt", "payslip", "lohnabrechnung", "payment", "bonus", "compensation"]},
    },
    "50-59 Personal": {
        "51 Education": {"keywords": ["education", "school", "schule", "university", "universität", "degree", "diploma", "course", "kurs", "grade"]},
        "52 Travel": {"keywords": ["travel", "reise", "flight", "flug", "hotel", "booking", "itinerary"]},
        "53 Certificates": {"keywords": ["certificate", "urkunde", "marriage", "heirat"]},
        "54 Memberships": {"keywords": ["membership", "mitgliedschaft", "club", "verein", "subscription"]},
        "55 Operation Manual": {"keywords": ["manual", "anleitung", "instruction", "guide", "handbuch", "user guide"]},
        "56 Health and Wellbeing": {"keywords": ["health", "wellness", "fitness", "nutrition", "exercise", "mental health"]},
        "57 IDs": {"keywords": ["id card", "identification", "badge", "employee id", "student id"]},
    },
    "90-99 Archive": {
        "91 2024": {"keywords": []},
        "92 2023": {"keywords": []},
    },
}

# Flat list of categories for keyword matching
JD_KEYWORDS = {}
for area, categories in JD_AREAS.items():
    for category, config in categories.items():
        JD_KEYWORDS[(area, category)] = config.get("keywords", [])

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

            # Resize very large images to avoid memory issues during OCR
            max_dimension = 10000  # pixels
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            text = pytesseract.image_to_string(img)
            return {"success": True, "text": text, "metadata": {"type": "image"}}
        
        else:
            return {"success": False, "text": "", "error": f"Unsupported format: {suffix}"}
            
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}


# ==============================================================================
# AI CATEGORIZATION
# ==============================================================================

def categorize_with_keywords(text: str, jd_areas: dict = None) -> dict:
    """Simple keyword-based categorization using Johnny.Decimal (no API needed)."""
    if jd_areas is None:
        jd_areas = JD_AREAS

    text_lower = text.lower()
    scores = {}

    # Score each JD category
    for area, categories in jd_areas.items():
        if area == "00-09 System" or area == "90-99 Archive":
            continue  # Skip system and archive areas
        for category, config in categories.items():
            keywords = config.get("keywords", [])
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[(area, category)] = score

    # Find best category
    if scores and max(scores.values()) > 0:
        best = max(scores, key=scores.get)
        jd_area, jd_category = best
    else:
        # Default fallback
        jd_area = "50-59 Personal"
        jd_category = "54 Memberships"

    # Simple tag extraction - find matching keywords
    tags = []
    for (area, category), keywords in JD_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower and kw not in tags:
                tags.append(kw)

    return {
        "jd_area": jd_area,
        "jd_category": jd_category,
        "tags": tags[:10],  # Limit to 10 tags
        "confidence": "low",
        "summary": text[:200] + "..." if len(text) > 200 else text,
        "correspondent": None,
        "date_mentioned": None,
        "entities": []
    }


def categorize_with_claude_code(text: str, jd_areas: dict = None, folder_hint: str = None) -> dict:
    """Use Claude Code CLI (works with Max subscription) to categorize using Johnny.Decimal.

    folder_hint: Optional folder name that provides context (e.g., "Salary Slips 2024")
    """
    import subprocess

    if jd_areas is None:
        jd_areas = JD_AREAS

    # Truncate text if too long
    max_chars = 6000
    truncated_text = text[:max_chars] if len(text) > max_chars else text

    # Build JD structure for prompt
    jd_structure = {}
    for area, categories in jd_areas.items():
        if area == "00-09 System":
            # Only include Uncategorized from System area
            jd_structure[area] = ["09 Uncategorized"]
        elif area != "90-99 Archive":
            jd_structure[area] = list(categories.keys())

    # Add folder context if provided
    folder_context = ""
    if folder_hint:
        folder_context = f"""
IMPORTANT CONTEXT: This file came from a folder named "{folder_hint}".
The folder name is a strong hint about what type of documents these are (e.g., "Salary Slips" suggests employment/payslips, "Medical Reports" suggests medical records).
Use this context to help categorize the document appropriately.
"""

    prompt = f"""You are a document categorization assistant using the Johnny.Decimal system.

Available Johnny.Decimal areas and categories:
{json.dumps(jd_structure, indent=2)}
{folder_context}
Analyze this document and categorize it.

Document content:
---
{truncated_text}
---

IMPORTANT naming rules:
- "document_type" should describe WHAT the document is (e.g., "Blood Test Results", "Employment Contract", "Insurance Card")
- "issuer" should be the organization/entity that CREATED or ISSUED the document (e.g., "Charité Hospital", "TK Insurance", "AutoScout24")
- Do NOT use the document subject's personal name as issuer (e.g., if it's a medical report FOR "John Smith", the issuer is the hospital, not John Smith)
- "subject_person" should ONLY be filled if the document is about someone OTHER than the system owner (e.g., spouse's documents)
- Use "00-09 System" / "09 Uncategorized" for research papers, academic articles, miscellaneous documents, or anything that doesn't clearly fit into the other categories

Respond with ONLY valid JSON in this exact format (no other text):
{{"jd_area": "one of the areas like 10-19 Finance", "jd_category": "one of the categories like 14 Receipts", "document_type": "specific type like Blood Test Results or Employment Contract", "issuer": "organization that created/issued the document", "subject_person": "only if document is about someone other than system owner, otherwise null", "tags": ["tag1", "tag2"], "confidence": "high/medium/low", "summary": "One sentence summary", "date_mentioned": "YYYY-MM-DD or null", "entities": ["organization names", "relevant identifiers"]}}"""

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
        logger.warning("Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return None
    except Exception as e:
        logger.warning(f"Claude Code categorization failed: {e}")
        return None


def categorize_with_llm(text: str, jd_areas: dict = None, api_key: Optional[str] = None, folder_hint: str = None) -> dict:
    """Use Claude API to categorize using Johnny.Decimal.

    folder_hint: Optional folder name that provides context (e.g., "Salary Slips 2024")
    """

    if jd_areas is None:
        jd_areas = JD_AREAS

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        logger.warning("No API key found, using keyword-based categorization")
        return categorize_with_keywords(text, jd_areas)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Truncate text if too long
        max_chars = 8000
        truncated_text = text[:max_chars] if len(text) > max_chars else text

        # Build JD structure for prompt
        jd_structure = {}
        for area, categories in jd_areas.items():
            if area == "00-09 System":
                # Only include Uncategorized from System area
                jd_structure[area] = ["09 Uncategorized"]
            elif area != "90-99 Archive":
                jd_structure[area] = list(categories.keys())

        # Add folder context if provided
        folder_context = ""
        if folder_hint:
            folder_context = f"""
IMPORTANT CONTEXT: This file came from a folder named "{folder_hint}".
The folder name is a strong hint about what type of documents these are (e.g., "Salary Slips" suggests employment/payslips, "Medical Reports" suggests medical records).
Use this context to help categorize the document appropriately.
"""

        prompt = f"""You are a document categorization assistant using the Johnny.Decimal system.

Available Johnny.Decimal areas and categories:
{json.dumps(jd_structure, indent=2)}
{folder_context}
Analyze this document and categorize it.

Document content:
---
{truncated_text}
---

IMPORTANT naming rules:
- "document_type" should describe WHAT the document is (e.g., "Blood Test Results", "Employment Contract", "Insurance Card")
- "issuer" should be the organization/entity that CREATED or ISSUED the document (e.g., "Charité Hospital", "TK Insurance", "AutoScout24")
- Do NOT use the document subject's personal name as issuer (e.g., if it's a medical report FOR "John Smith", the issuer is the hospital, not John Smith)
- "subject_person" should ONLY be filled if the document is about someone OTHER than the system owner (e.g., spouse's documents)
- Use "00-09 System" / "09 Uncategorized" for research papers, academic articles, miscellaneous documents, or anything that doesn't clearly fit into the other categories

Respond with ONLY valid JSON in this exact format:
{{
    "jd_area": "one of the areas like 10-19 Finance",
    "jd_category": "one of the categories like 14 Receipts",
    "document_type": "specific type like Blood Test Results or Employment Contract",
    "issuer": "organization that created/issued the document",
    "subject_person": "only if document is about someone other than system owner, otherwise null",
    "tags": ["tag1", "tag2", "tag3"],
    "confidence": "high/medium/low",
    "summary": "One sentence summary of the document",
    "date_mentioned": "YYYY-MM-DD if a date is found, null otherwise",
    "entities": ["organization names", "relevant identifiers"]
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
        logger.error(f"LLM categorization failed: {e}")
        return categorize_with_keywords(text, jd_areas)


# ==============================================================================
# FILE ORGANIZATION - JOHNNY.DECIMAL
# ==============================================================================

def get_jd_ids_path(output_dir: str) -> Path:
    """Get path to the JD IDs tracking file."""
    return Path(output_dir) / ".jd_ids.json"


def load_jd_ids(output_dir: str) -> dict:
    """Load the JD IDs tracking database."""
    ids_path = get_jd_ids_path(output_dir)
    if ids_path.exists():
        try:
            with open(ids_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_jd_ids(output_dir: str, jd_ids: dict):
    """Save the JD IDs tracking database."""
    ids_path = get_jd_ids_path(output_dir)
    ids_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ids_path, 'w') as f:
        json.dump(jd_ids, f, indent=2, ensure_ascii=False)


def get_or_create_jd_id(output_dir: str, jd_category: str, correspondent: str, year: str) -> str:
    """Get existing or create new JD ID for a correspondent+year combination."""
    jd_ids = load_jd_ids(output_dir)

    # Initialize category tracking if needed
    if jd_category not in jd_ids:
        jd_ids[jd_category] = {"next_id": 1, "mappings": {}}

    # Create key for this correspondent+year
    key = f"{correspondent}_{year}"

    # Check if we already have an ID for this combination
    if key in jd_ids[jd_category]["mappings"]:
        return jd_ids[jd_category]["mappings"][key]

    # Create new ID
    cat_num = jd_category.split()[0]  # e.g., "14" from "14 Receipts"
    id_num = jd_ids[jd_category]["next_id"]
    jd_id = f"{cat_num}.{id_num:02d}"

    # Save mapping
    jd_ids[jd_category]["mappings"][key] = jd_id
    jd_ids[jd_category]["next_id"] = id_num + 1
    save_jd_ids(output_dir, jd_ids)

    return jd_id


def slugify(text: str, max_length: int = 30) -> str:
    """Convert text to a clean slug for filenames.

    Converts to lowercase, replaces spaces with underscores, removes special chars.
    """
    if not text:
        return "unknown"
    # Replace spaces and common separators with underscores
    slug = text.lower().replace(" ", "_").replace("-", "_")
    # Remove problematic chars, keep alphanumeric and underscores
    slug = "".join(c if c.isalnum() or c == "_" else "" for c in slug)
    # Collapse multiple underscores
    while "__" in slug:
        slug = slug.replace("__", "_")
    # Trim underscores from ends
    slug = slug.strip("_")
    return slug[:max_length] if slug else "unknown"


def generate_filename(original_name: str, analysis: dict, jd_id: str = "", year: str = "") -> str:
    """Generate a descriptive filename based on analysis.

    Format: {JD_ID} {Issuer} {Document_Type} {Year}.ext
    Example: 14.01 Amazon Laptop Receipt 2024.pdf
    """
    suffix = Path(original_name).suffix

    # Get issuer and document type from analysis
    issuer = analysis.get("issuer", "")
    document_type = analysis.get("document_type", "")
    subject_person = analysis.get("subject_person")

    # Clean up issuer - remove trailing punctuation, normalize spaces
    if issuer:
        issuer = issuer.strip().rstrip(".,;:")
        # Replace problematic filesystem chars
        issuer = issuer.replace("/", "_").replace("\\", "_").replace(":", "_")

    # Clean up document type
    if document_type:
        document_type = document_type.strip().rstrip(".,;:")
        document_type = document_type.replace("/", "_").replace("\\", "_").replace(":", "_")

    # Build the descriptor parts
    parts = []
    if issuer:
        parts.append(issuer)
    if document_type:
        parts.append(document_type)

    # Add subject person if it's someone other than the system owner
    if subject_person and subject_person.lower() not in ["null", "none", ""]:
        parts.append(f"({subject_person})")

    if parts:
        descriptor = " ".join(parts)
    else:
        # Fallback: use original filename stem
        stem = Path(original_name).stem
        # Remove date prefix if present (e.g., "20241220_something")
        if len(stem) > 8 and stem[:8].isdigit():
            stem = stem[9:] if len(stem) > 9 else stem
        descriptor = stem.replace("_", " ").title()

    # Limit descriptor length for filesystem compatibility
    descriptor = descriptor[:50]

    # Use provided year or extract from analysis
    if not year:
        year = extract_year(analysis)

    # Build final filename: "{JD_ID} {Descriptor} {Year}.ext"
    if jd_id:
        return f"{jd_id} {descriptor} {year}{suffix}"
    else:
        return f"{descriptor} {year}{suffix}"


def create_metadata_file(file_path: str, analysis: dict, original_name: str, jd_id: str, extracted_text: str = ""):
    """Create a JSON sidecar file with JD metadata and extracted text."""
    metadata = {
        "id": jd_id,
        "jd_area": analysis.get("jd_area"),
        "jd_category": analysis.get("jd_category"),
        "document_type": analysis.get("document_type"),
        "issuer": analysis.get("issuer"),
        "subject_person": analysis.get("subject_person"),
        "correspondent": analysis.get("correspondent"),  # Keep for backwards compatibility
        "original_filename": original_name,
        "current_filename": Path(file_path).name,
        "organized_date": datetime.now().isoformat(),
        "document_date": analysis.get("date_mentioned"),
        "tags": analysis.get("tags", []),
        "summary": analysis.get("summary", ""),
        "confidence": analysis.get("confidence", ""),
        "entities": analysis.get("entities", []),
        "extracted_text": extracted_text
    }

    metadata_path = Path(file_path).with_suffix(Path(file_path).suffix + ".meta.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def generate_folder_descriptor(analysis: dict, original_name: str) -> str:
    """Generate a descriptive folder name from analysis.

    Format: {Issuer} {Document_Type}
    Example: "Charité Blood Test Results" or "TK Insurance Card"

    Falls back to issuer-only or document-type-only if one is missing.
    """
    issuer = analysis.get("issuer", "")
    document_type = analysis.get("document_type", "")
    subject_person = analysis.get("subject_person")

    # Clean up issuer - remove trailing punctuation, normalize spaces
    if issuer:
        issuer = issuer.strip().rstrip(".,;:")
        # Replace problematic filesystem chars
        issuer = issuer.replace("/", "_").replace("\\", "_").replace(":", "_")

    # Clean up document type
    if document_type:
        document_type = document_type.strip().rstrip(".,;:")
        document_type = document_type.replace("/", "_").replace("\\", "_").replace(":", "_")

    # Build the descriptor
    parts = []
    if issuer:
        parts.append(issuer)
    if document_type:
        parts.append(document_type)

    # Add subject person if it's someone other than the system owner
    if subject_person and subject_person.lower() not in ["null", "none", ""]:
        parts.append(f"({subject_person})")

    if parts:
        descriptor = " ".join(parts)
    else:
        # Fallback: use original filename stem
        stem = Path(original_name).stem
        # Remove date prefix if present (e.g., "20241220_something")
        if len(stem) > 8 and stem[:8].isdigit():
            stem = stem[9:] if len(stem) > 9 else stem
        descriptor = stem.replace("_", " ").title()

    # Limit length for filesystem compatibility
    return descriptor[:60]


def extract_year(analysis: dict) -> str:
    """Extract year from analysis."""
    date_mentioned = analysis.get("date_mentioned")
    if date_mentioned:
        try:
            return date_mentioned[:4]
        except (TypeError, IndexError):
            pass
    return str(datetime.now().year)


def organize_file(file_path: str, output_dir: str, analysis: dict, extracted_text: str = "") -> str:
    """Move file to Johnny.Decimal folder structure (flat).

    Structure: output/Area/Category/{JD_ID} {Issuer} {DocType} {Year}.ext
    Example: output/10-19 Finance/14 Receipts/14.01 Amazon Laptop Receipt 2024.pdf
    """
    jd_area = analysis.get("jd_area", "50-59 Personal")
    jd_category = analysis.get("jd_category", "54 Memberships")

    # Generate folder descriptor from issuer + document type
    original_name = Path(file_path).name
    folder_descriptor = generate_folder_descriptor(analysis, original_name)
    year = extract_year(analysis)

    # Get or create JD ID for this issuer+year combination
    jd_id = get_or_create_jd_id(output_dir, jd_category, folder_descriptor, year)

    # Create folder structure: output/Area/Category/ (flat, no sub-folder per document)
    dest_dir = Path(output_dir) / jd_area / jd_category
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Generate new filename with JD ID: "14.01 Amazon Laptop Receipt 2024.pdf"
    new_name = generate_filename(original_name, analysis, jd_id, year)
    dest_path = dest_dir / new_name

    # Handle duplicates - add suffix
    counter = 1
    while dest_path.exists():
        stem = Path(new_name).stem
        suffix = Path(new_name).suffix
        dest_path = dest_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    # Get file hash before moving (for hash index)
    file_hash = get_file_hash(file_path)

    # Move the file
    shutil.move(file_path, dest_path)

    # Create metadata sidecar with extracted text
    create_metadata_file(str(dest_path), analysis, original_name, jd_id, extracted_text)

    # Add to central search index
    add_to_search_index(output_dir, str(dest_path), original_name, analysis, extracted_text)

    # Add to hash index for duplicate detection
    add_to_hash_index(output_dir, file_hash, str(dest_path))

    # Update JDex index
    update_jdex_index(output_dir, jd_id, jd_area, jd_category, folder_descriptor, year,
                      Path(dest_path).name, analysis.get("summary", ""))

    return str(dest_path)


def update_jdex_index(output_dir: str, jd_id: str, jd_area: str, jd_category: str,
                      correspondent: str, year: str, filename: str, summary: str):
    """Append a new entry to the JDex index file."""
    index_path = Path(output_dir) / "00-09 System" / "00 Index" / "00.00 Index.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    entry = f"""
#### {jd_id} {correspondent} {year}
Location: file system

- {filename}
  {summary[:100]}{'...' if len(summary) > 100 else ''}

"""

    # Append to index file (or create if doesn't exist)
    mode = 'a' if index_path.exists() else 'w'
    with open(index_path, mode) as f:
        if mode == 'w':
            f.write(f"# JDex Index\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n")
        f.write(entry)


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
        "jd_area": analysis.get("jd_area"),
        "jd_category": analysis.get("jd_category"),
        "correspondent": analysis.get("correspondent"),
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
    """Generate a hash based on file content using SHA256."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


# ==============================================================================
# LOCAL HASH INDEX - Duplicate Detection
# ==============================================================================

def get_hash_index_path(output_dir: str) -> Path:
    """Get path to the local hash index file."""
    return Path(output_dir) / ".hash_index.json"


def load_hash_index(output_dir: str) -> dict:
    """Load the local hash index from JSON.

    Returns dict mapping file_hash -> file_path
    """
    index_path = get_hash_index_path(output_dir)
    if index_path.exists():
        try:
            with open(index_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_hash_index(output_dir: str, index: dict):
    """Save the local hash index to JSON."""
    index_path = get_hash_index_path(output_dir)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def add_to_hash_index(output_dir: str, file_hash: str, file_path: str):
    """Add a file to the hash index."""
    index = load_hash_index(output_dir)
    index[file_hash] = file_path
    save_hash_index(output_dir, index)


def find_duplicate_in_index(output_dir: str, file_path: str) -> str | None:
    """Check if a file's content already exists in the output directory.

    Returns the path to the existing file if duplicate found, None otherwise.
    """
    file_hash = get_file_hash(file_path)
    index = load_hash_index(output_dir)

    existing_path = index.get(file_hash)
    if existing_path:
        # Verify the file still exists (could have been deleted)
        if Path(existing_path).exists():
            return existing_path
        else:
            # File was deleted, remove from index
            del index[file_hash]
            save_hash_index(output_dir, index)

    return None


def build_hash_index(output_dir: str, force_rebuild: bool = False) -> dict:
    """Build or rebuild the hash index by scanning all files in output directory.

    Skips system files (starting with .) and metadata files (.meta.json, .analysis.json).

    Args:
        output_dir: The JD output directory to scan
        force_rebuild: If True, rebuild from scratch. If False, only add new files.

    Returns:
        The complete hash index
    """
    output_path = Path(output_dir)

    if force_rebuild:
        index = {}
        print(f"🔄 Rebuilding hash index from scratch...")
    else:
        index = load_hash_index(output_dir)
        print(f"📋 Loaded existing hash index with {len(index)} entries")

    # Track existing hashes to detect stale entries
    found_hashes = set()
    new_files = 0

    # Scan all files in output directory
    for file_path in output_path.rglob('*'):
        if not file_path.is_file():
            continue

        # Skip hidden/system files
        if file_path.name.startswith('.'):
            continue

        # Skip metadata sidecar files
        if file_path.name.endswith('.meta.json') or file_path.name.endswith('.analysis.json'):
            continue

        # Skip unsupported formats
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            continue

        # Skip inbox directory
        try:
            relative = file_path.relative_to(output_path)
            if relative.parts[0] == "00-09 System" and len(relative.parts) > 1 and relative.parts[1] == "01 Inbox":
                continue
        except (ValueError, IndexError):
            pass

        # Hash the file
        try:
            file_hash = get_file_hash(str(file_path))
            found_hashes.add(file_hash)

            if file_hash not in index:
                index[file_hash] = str(file_path)
                new_files += 1
                if force_rebuild:
                    print(f"  📄 Indexed: {file_path.name}")
        except (IOError, OSError) as e:
            logger.warning(f"Could not hash {file_path}: {e}")

    # Remove stale entries (files that no longer exist)
    stale_hashes = set(index.keys()) - found_hashes
    for stale_hash in stale_hashes:
        del index[stale_hash]

    if stale_hashes:
        print(f"🗑️  Removed {len(stale_hashes)} stale entries")

    save_hash_index(output_dir, index)
    print(f"✅ Hash index complete: {len(index)} files indexed ({new_files} new)")

    return index


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
# PREPROCESSING (extract + analyze, but don't move)
# ==============================================================================

def get_analysis_path(file_path: str) -> Path:
    """Get path to the analysis JSON file for a document."""
    return Path(file_path).with_suffix(Path(file_path).suffix + ".analysis.json")


def has_analysis(file_path: str) -> bool:
    """Check if a document already has an analysis file."""
    return get_analysis_path(file_path).exists()


def load_analysis(file_path: str) -> dict | None:
    """Load existing analysis for a document."""
    analysis_path = get_analysis_path(file_path)
    if analysis_path.exists():
        try:
            with open(analysis_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def save_analysis(file_path: str, analysis: dict, extracted_text: str):
    """Save analysis to a sidecar JSON file."""
    analysis_path = get_analysis_path(file_path)
    data = {
        **analysis,
        "extracted_text": extracted_text,
        "original_filename": Path(file_path).name,
        "analyzed_at": datetime.now().isoformat(),
    }
    with open(analysis_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def preprocess_file(file_path: str, jd_areas: dict = None, mode: str = "claude-code", folder_hint: str = None) -> dict:
    """Extract text and generate AI analysis, saving to .analysis.json sidecar.

    Does NOT move the file - leaves it in inbox for manual classification via UI.

    mode: "claude-code" (uses Max subscription), "api" (uses ANTHROPIC_API_KEY), "keywords" (no AI)
    folder_hint: Optional folder name that provides context for categorization
    """
    if jd_areas is None:
        jd_areas = JD_AREAS

    print(f"\n📄 Preprocessing: {Path(file_path).name}")
    if folder_hint:
        print(f"  📁 Folder context: {folder_hint}")

    # Check if already analyzed
    if has_analysis(file_path):
        print(f"  ⏭️  Already has analysis, skipping")
        return {"success": True, "skipped": True, "file": file_path}

    # Step 1: Extract text
    print("  📖 Extracting text...")
    result = extract_text_with_docling(file_path)

    if not result["success"]:
        print(f"  ⚠️  Docling failed, trying fallback: {result.get('error', 'unknown')}")
        result = extract_text_fallback(file_path)

    if not result["success"] or not result["text"].strip():
        print(f"  ❌ Could not extract text from file")
        return {"success": False, "error": "Text extraction failed", "file": file_path}

    extracted_text = result["text"]
    print(f"  ✅ Extracted {len(extracted_text)} characters")

    # Step 2: Get AI analysis
    print("  🤖 Analyzing content...")
    analysis = None

    if mode == "claude-code":
        analysis = categorize_with_claude_code(extracted_text, jd_areas, folder_hint=folder_hint)
        if analysis is None:
            print("  ⚠️  Falling back to keyword matching")
            analysis = categorize_with_keywords(extracted_text, jd_areas)
    elif mode == "api":
        analysis = categorize_with_llm(extracted_text, jd_areas, folder_hint=folder_hint)
    else:
        analysis = categorize_with_keywords(extracted_text, jd_areas)

    jd_area = analysis.get('jd_area', '50-59 Personal')
    jd_category = analysis.get('jd_category', '54 Memberships')
    print(f"  📁 AI suggests: {jd_area} / {jd_category}")
    print(f"  🏷️  Tags: {', '.join(analysis.get('tags', [])[:5])}")

    # Step 3: Save analysis (but don't move file)
    save_analysis(file_path, analysis, extracted_text)
    print(f"  💾 Saved analysis to: {get_analysis_path(file_path).name}")

    return {
        "success": True,
        "file": file_path,
        "analysis": analysis,
    }


def get_folder_hint(file_path: Path, inbox_dir: Path) -> str | None:
    """Get folder hint for a file if it's in a subfolder of the inbox.

    Returns the immediate parent folder name if the file is in a subfolder,
    None if the file is directly in the inbox.
    """
    try:
        relative = file_path.relative_to(inbox_dir)
        parts = relative.parts
        # If file is in a subfolder, return the subfolder name
        if len(parts) > 1:
            return parts[0]  # First subfolder name
    except ValueError:
        pass
    return None


def preprocess_inbox(inbox_dir: str, jd_areas: dict = None, mode: str = "claude-code") -> list:
    """Preprocess all files in inbox - extract text and generate AI analysis.

    Recursively scans subfolders and uses folder names as context hints for categorization.
    """
    if jd_areas is None:
        jd_areas = JD_AREAS

    print(f"\n📥 Preprocessing inbox: {inbox_dir}")
    print(f"🤖 Mode: {mode}")
    print(f"📂 Scanning subfolders recursively\n")

    inbox = Path(inbox_dir)

    results = []
    # Use rglob to recursively find all files
    for file_path in inbox.rglob('*'):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            continue
        # Skip analysis files themselves
        if file_path.name.endswith('.analysis.json'):
            continue

        # Get folder hint if file is in a subfolder
        folder_hint = get_folder_hint(file_path, inbox)

        result = preprocess_file(str(file_path), jd_areas, mode, folder_hint=folder_hint)
        results.append(result)

    # Summary
    successful = sum(1 for r in results if r.get("success"))
    skipped = sum(1 for r in results if r.get("skipped"))
    print(f"\n{'='*50}")
    print(f"✅ Preprocessed {successful}/{len(results)} files")
    if skipped:
        print(f"⏭️  Skipped {skipped} already analyzed files")

    return results


def watch_preprocess(inbox_dir: str, jd_areas: dict = None, mode: str = "claude-code", interval: int = 5):
    """Watch inbox and preprocess new files (extract + analyze only, no moving).

    Recursively scans subfolders and uses folder names as context hints.
    """
    if jd_areas is None:
        jd_areas = JD_AREAS

    print(f"\n👁️  Watching folder for preprocessing: {inbox_dir}")
    print(f"🤖 Mode: {mode}")
    print(f"📂 Scanning subfolders recursively")
    print(f"🔄 Checking every {interval} seconds (Ctrl+C to stop)")
    print(f"📝 Files will be analyzed but NOT moved - use UI to classify\n")

    while True:
        try:
            inbox = Path(inbox_dir)

            # Use rglob to recursively find all files
            for file_path in inbox.rglob('*'):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in SUPPORTED_FORMATS:
                    continue
                # Skip analysis files
                if file_path.name.endswith('.analysis.json'):
                    continue
                # Skip if already analyzed
                if has_analysis(str(file_path)):
                    continue

                # Get folder hint if file is in a subfolder
                folder_hint = get_folder_hint(file_path, inbox)

                preprocess_file(str(file_path), jd_areas, mode, folder_hint=folder_hint)

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n👋 Stopping watcher...")
            break


# ==============================================================================
# MAIN PROCESSING
# ==============================================================================

def process_file(file_path: str, output_dir: str, jd_areas: dict = None, mode: str = "claude-code") -> dict:
    """Process a single file: extract, categorize, organize using Johnny.Decimal.

    mode: "claude-code" (uses Max subscription), "api" (uses ANTHROPIC_API_KEY), "keywords" (no AI)
    """
    if jd_areas is None:
        jd_areas = JD_AREAS

    print(f"\n📄 Processing: {Path(file_path).name}")

    # Step 0: Check for duplicates in hash index
    existing_file = find_duplicate_in_index(output_dir, file_path)
    if existing_file:
        print(f"  ⚠️  Duplicate detected!")
        print(f"  📍 Already exists: {existing_file}")
        # Remove the duplicate from inbox
        Path(file_path).unlink()
        print(f"  🗑️  Removed duplicate from inbox")
        return {
            "success": False,
            "error": "Duplicate file",
            "duplicate_of": existing_file
        }

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

    # Step 2: Categorize using Johnny.Decimal
    print("  🤖 Analyzing content...")
    analysis = None

    if mode == "claude-code":
        analysis = categorize_with_claude_code(result["text"], jd_areas)
        if analysis is None:
            print("  ⚠️  Falling back to keyword matching")
            analysis = categorize_with_keywords(result["text"], jd_areas)
    elif mode == "api":
        analysis = categorize_with_llm(result["text"], jd_areas)
    else:
        analysis = categorize_with_keywords(result["text"], jd_areas)

    jd_area = analysis.get('jd_area', '50-59 Personal')
    jd_category = analysis.get('jd_category', '54 Memberships')
    print(f"  📁 JD: {jd_area} / {jd_category}")
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


def watch_folder(inbox_dir: str, output_dir: str, jd_areas: dict = None, mode: str = "claude-code", interval: int = 5):
    """Watch inbox folder and process new files using Johnny.Decimal."""
    if jd_areas is None:
        jd_areas = JD_AREAS

    print(f"\n👁️  Watching folder: {inbox_dir}")
    print(f"📤 Output folder: {output_dir}")
    print(f"🤖 Mode: {mode}")
    print(f"📂 Using Johnny.Decimal organization")
    print(f"🔄 Checking every {interval} seconds (Ctrl+C to stop)\n")

    # Load persistent processed files database
    processed = load_processed_files(output_dir)
    print(f"📋 Loaded {len(processed)} previously processed files from database\n")

    while True:
        try:
            inbox = Path(inbox_dir)

            for file_path in inbox.iterdir():
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() not in SUPPORTED_FORMATS:
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
                result = process_file(str(file_path), output_dir, jd_areas, mode)

                if result.get("success"):
                    mark_file_processed(file_hash, original_name, result["destination"], processed)
                    save_processed_files(output_dir, processed)

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n👋 Stopping watcher...")
            break


def process_once(inbox_dir: str, output_dir: str, jd_areas: dict = None, mode: str = "claude-code"):
    """Process all files in inbox once (no watching) using Johnny.Decimal."""
    if jd_areas is None:
        jd_areas = JD_AREAS

    print(f"\n📥 Processing all files in: {inbox_dir}")
    print(f"📤 Output folder: {output_dir}")
    print(f"🤖 Mode: {mode}")
    print(f"📂 Using Johnny.Decimal organization\n")

    # Load persistent processed files database
    processed = load_processed_files(output_dir)
    print(f"📋 Loaded {len(processed)} previously processed files from database\n")

    inbox = Path(inbox_dir)

    results = []
    skipped = 0
    for file_path in inbox.iterdir():
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
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

        result = process_file(str(file_path), output_dir, jd_areas, mode)
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

# Default paths from config.yaml (with env var and home directory fallbacks)
DEFAULT_JD_OUTPUT = CONFIG["paths"]["output_dir"]
DEFAULT_JD_INBOX = CONFIG["paths"]["inbox_dir"]


def main():
    parser = argparse.ArgumentParser(
        description="Automatically organize documents using AI and Johnny.Decimal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Johnny.Decimal Organization System
==================================
Documents are organized into a hierarchical structure:
  Area → Category → ID Folder → Files

Example: 10-19 Finance/14 Receipts/14.01 Amazon 2024/2024-12-20_laptop.pdf

Examples:
  # Preprocess only - extract text + AI analysis, save .json (use with UI)
  python document_organizer.py --preprocess

  # Preprocess once (no watching)
  python document_organizer.py --preprocess --once

  # Full auto-processing (extract, analyze, AND move files)
  python document_organizer.py --inbox ./inbox --output ./jd_documents

  # Use API key instead
  python document_organizer.py --inbox ./inbox --output ./jd_documents --mode api

  # Use only keyword matching (no AI needed)
  python document_organizer.py --inbox ./inbox --output ./jd_documents --mode keywords

  # Process all files once (don't watch)
  python document_organizer.py --inbox ./inbox --output ./jd_documents --once

  # Rebuild hash index (scan all files in output, update .hash_index.json)
  python document_organizer.py --rebuild-index

Modes:
  claude-code  Use Claude Code CLI (works with Max subscription, no API key needed)
  api          Use Anthropic API (requires ANTHROPIC_API_KEY env variable)
  keywords     Simple keyword matching (no AI, always works)

JD Areas:
  10-19 Finance   Banking, Taxes, Insurance, Receipts, Bills
  20-29 Medical   Records, Insurance, Prescriptions, Dental, Vision
  30-39 Legal     Contracts, Property, Identity, Warranties
  40-49 Work      Employment, Expenses, Projects, Certifications
  50-59 Personal  Education, Travel, Certificates, Memberships
        """
    )

    parser.add_argument("--inbox", "-i",
                        default=DEFAULT_JD_INBOX,
                        help="Input folder to watch/process")
    parser.add_argument("--output", "-o",
                        default=DEFAULT_JD_OUTPUT,
                        help="Output folder for organized files (JD root)")
    parser.add_argument("--once", action="store_true", help="Process once and exit (don't watch)")
    parser.add_argument("--preprocess", "-p", action="store_true",
                        help="Preprocess only: extract text + AI analysis, save .json (for use with UI)")
    parser.add_argument("--mode", "-m", choices=["claude-code", "api", "keywords"],
                        default="claude-code", help="Categorization mode (default: claude-code)")
    parser.add_argument("--interval", type=int, default=5, help="Watch interval in seconds (default: 5)")
    parser.add_argument("--rebuild-index", action="store_true",
                        help="Rebuild hash index by scanning all files in output directory")

    # Legacy flag for backwards compatibility
    parser.add_argument("--no-llm", action="store_true", help="(deprecated) Use --mode keywords instead")

    args = parser.parse_args()

    # Handle legacy flag
    mode = args.mode
    if args.no_llm:
        mode = "keywords"

    # Rebuild hash index mode
    if args.rebuild_index:
        if not args.output:
            parser.error("--output is required for --rebuild-index")
        build_hash_index(args.output, force_rebuild=True)
        return

    # Validate required paths
    if not args.inbox:
        parser.error("--inbox is required (or set INBOX_DIR in .env)")

    # Create inbox directory
    Path(args.inbox).mkdir(parents=True, exist_ok=True)

    # Preprocess mode: extract + analyze only, don't move files
    if args.preprocess:
        if args.once:
            preprocess_inbox(args.inbox, JD_AREAS, mode)
        else:
            watch_preprocess(args.inbox, JD_AREAS, mode, args.interval)
        return

    # Full processing mode: requires output directory
    if not args.output:
        parser.error("--output is required (or set OUTPUT_DIR in .env)")

    Path(args.output).mkdir(parents=True, exist_ok=True)

    if args.once:
        process_once(args.inbox, args.output, JD_AREAS, mode)
    else:
        watch_folder(args.inbox, args.output, JD_AREAS, mode, args.interval)


if __name__ == "__main__":
    main()