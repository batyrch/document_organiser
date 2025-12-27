#!/usr/bin/env python3
"""
JSON-RPC API Server for Electron IPC.

Reads JSON commands from stdin, calls document_organizer functions,
and writes JSON responses to stdout. Designed for use with Electron's
child_process spawn.

Protocol:
  - Each request is a single line of JSON
  - Each response is a single line of JSON
  - Format: {"id": "uuid", "method": "...", "params": {...}}
  - Response: {"id": "uuid", "result": {...}, "error": null}

Methods:
  - files:list - List files in a directory
  - files:analyze - Extract text and run AI categorization
  - files:move - Move file to JD location
  - files:delete - Delete file and its metadata
  - settings:get - Get all settings
  - settings:set - Update a setting
  - jd:getAreas - Get JD structure
  - thumbnails:generate - Generate thumbnail for a file
"""

import json
import sys
import os
import traceback
from pathlib import Path
from typing import Any, Optional

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from document_organizer import (
    extract_text_with_docling,
    extract_text_fallback,
    get_merged_jd_areas,
    load_analysis,
    save_analysis,
    organize_file,
    SUPPORTED_FORMATS,
)
from settings import get_settings
from ai_providers import get_provider, categorize_document


def log_debug(msg: str):
    """Log debug messages to stderr (so they don't interfere with stdout JSON)."""
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)


def send_response(request_id: str, result: Any = None, error: Optional[str] = None):
    """Send a JSON response to stdout."""
    response = {
        "id": request_id,
        "result": result,
        "error": error,
    }
    # Write as single line, then flush
    print(json.dumps(response), flush=True)


def handle_files_list(params: dict) -> dict:
    """List files in a directory."""
    folder = params.get("folder")
    recursive = params.get("recursive", False)

    if not folder:
        raise ValueError("folder parameter is required")

    folder_path = Path(folder)
    if not folder_path.exists():
        raise ValueError(f"Folder does not exist: {folder}")

    files = []

    if recursive:
        iterator = folder_path.rglob("*")
    else:
        iterator = folder_path.iterdir()

    for file_path in iterator:
        if not file_path.is_file():
            continue

        # Skip hidden files and metadata files
        if file_path.name.startswith("."):
            continue
        if file_path.name.endswith(".meta.json"):
            continue

        # Check if it's a supported format
        suffix = file_path.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            continue

        # Get file info
        stat = file_path.stat()

        # Check for existing analysis
        analysis = load_analysis(str(file_path))

        files.append({
            "path": str(file_path),
            "name": file_path.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "extension": suffix,
            "hasAnalysis": analysis is not None,
            "analysis": analysis,
        })

    # Sort by modification time (newest first)
    files.sort(key=lambda f: f["modified"], reverse=True)

    return {"files": files, "count": len(files)}


def handle_files_analyze(params: dict) -> dict:
    """Extract text and run AI categorization on a file."""
    file_path = params.get("filePath")
    force = params.get("force", False)
    folder_hint = params.get("folderHint")

    if not file_path:
        raise ValueError("filePath parameter is required")

    if not Path(file_path).exists():
        raise ValueError(f"File does not exist: {file_path}")

    # Check for existing analysis
    if not force:
        existing = load_analysis(file_path)
        if existing:
            return {
                "success": True,
                "cached": True,
                "analysis": existing,
            }

    # Extract text
    log_debug(f"Extracting text from: {file_path}")
    result = extract_text_with_docling(file_path)

    if not result["success"]:
        log_debug(f"Docling failed, trying fallback: {result.get('error')}")
        result = extract_text_fallback(file_path)

    if not result["success"] or not result["text"].strip():
        raise ValueError(f"Could not extract text: {result.get('error', 'No text found')}")

    extracted_text = result["text"]
    log_debug(f"Extracted {len(extracted_text)} characters")

    # Get JD areas
    settings = get_settings()
    jd_areas = get_merged_jd_areas(settings.output_dir)

    # Get effective AI provider
    provider_name = settings.get_effective_provider()
    log_debug(f"Using AI provider: {provider_name}")

    # Run categorization
    analysis = categorize_document(
        extracted_text,
        jd_areas,
        provider=provider_name,
        fallback_to_keywords=True,
    )

    if not analysis:
        raise ValueError("AI categorization failed")

    # Save analysis to sidecar file
    save_analysis(file_path, analysis, extracted_text)
    log_debug(f"Saved analysis for: {Path(file_path).name}")

    return {
        "success": True,
        "cached": False,
        "analysis": {
            **analysis,
            "extracted_text": extracted_text,
        },
    }


def handle_files_move(params: dict) -> dict:
    """Move file to JD location."""
    file_path = params.get("filePath")
    area = params.get("area")
    category = params.get("category")

    if not file_path:
        raise ValueError("filePath parameter is required")
    if not area:
        raise ValueError("area parameter is required")
    if not category:
        raise ValueError("category parameter is required")

    if not Path(file_path).exists():
        raise ValueError(f"File does not exist: {file_path}")

    # Load analysis or create minimal one
    analysis = load_analysis(file_path)
    if not analysis:
        # Create minimal analysis
        analysis = {
            "jd_area": area,
            "jd_category": category,
            "document_type": "Document",
            "issuer": "Unknown",
            "tags": [],
            "confidence": "low",
            "summary": "",
        }
    else:
        # Override with user selection
        analysis["jd_area"] = area
        analysis["jd_category"] = category

    # Get output directory
    settings = get_settings()
    output_dir = settings.output_dir

    # Get extracted text from analysis if available
    extracted_text = analysis.get("extracted_text", "")

    # Organize the file
    dest_path = organize_file(file_path, output_dir, analysis, extracted_text)

    # Delete the old meta file if it exists
    old_meta = Path(file_path).with_suffix(Path(file_path).suffix + ".meta.json")
    if old_meta.exists():
        old_meta.unlink()

    return {
        "success": True,
        "destination": dest_path,
        "analysis": analysis,
    }


def handle_files_delete(params: dict) -> dict:
    """Delete a file and its metadata."""
    file_path = params.get("filePath")

    if not file_path:
        raise ValueError("filePath parameter is required")

    file_p = Path(file_path)

    if not file_p.exists():
        raise ValueError(f"File does not exist: {file_path}")

    # Delete the file
    file_p.unlink()

    # Delete metadata sidecar if exists
    meta_path = file_p.with_suffix(file_p.suffix + ".meta.json")
    if meta_path.exists():
        meta_path.unlink()

    return {"success": True, "deleted": file_path}


def handle_settings_get(params: dict) -> dict:
    """Get all settings."""
    settings = get_settings()

    return {
        "output_dir": settings.output_dir,
        "inbox_dir": settings.inbox_dir,
        "ai_provider": settings.ai_provider,
        "effective_provider": settings.get_effective_provider(),
        "setup_complete": settings.setup_complete,
        "anthropic_model": settings.get("anthropic_model"),
        "openai_model": settings.get("openai_model"),
        "ollama_url": settings.get("ollama_url"),
        "ollama_model": settings.get("ollama_model"),
        "has_anthropic_key": bool(settings.get("anthropic_api_key")),
        "has_openai_key": bool(settings.get("openai_api_key")),
        "has_keychain_support": settings.has_keychain_support(),
    }


def handle_settings_set(params: dict) -> dict:
    """Update a setting."""
    key = params.get("key")
    value = params.get("value")

    if not key:
        raise ValueError("key parameter is required")

    settings = get_settings()
    settings.set(key, value)

    return {"success": True, "key": key}


def handle_jd_get_areas(params: dict) -> dict:
    """Get JD structure (areas and categories)."""
    settings = get_settings()
    jd_areas = get_merged_jd_areas(settings.output_dir)

    # Convert to a more structured format for the frontend
    areas = []
    for area_name, categories in jd_areas.items():
        cat_list = []
        for cat_name, cat_config in categories.items():
            cat_list.append({
                "name": cat_name,
                "keywords": cat_config.get("keywords", []),
            })
        areas.append({
            "name": area_name,
            "categories": cat_list,
        })

    return {"areas": areas}


def handle_thumbnails_generate(params: dict) -> dict:
    """Generate thumbnail for a file.

    Note: Thumbnail generation is handled in the main process using sharp.
    This method is here for potential future Python-based thumbnail generation.
    """
    file_path = params.get("filePath")

    if not file_path:
        raise ValueError("filePath parameter is required")

    # For now, just return the file path - actual thumbnail generation
    # happens in the Electron main process using sharp
    return {
        "filePath": file_path,
        "message": "Use main process for thumbnail generation",
    }


# Method dispatcher
METHODS = {
    "files:list": handle_files_list,
    "files:analyze": handle_files_analyze,
    "files:move": handle_files_move,
    "files:delete": handle_files_delete,
    "settings:get": handle_settings_get,
    "settings:set": handle_settings_set,
    "jd:getAreas": handle_jd_get_areas,
    "thumbnails:generate": handle_thumbnails_generate,
}


def handle_request(request: dict) -> None:
    """Handle a single JSON-RPC request."""
    request_id = request.get("id", "unknown")
    method = request.get("method")
    params = request.get("params", {})

    if not method:
        send_response(request_id, error="method is required")
        return

    if method not in METHODS:
        send_response(request_id, error=f"Unknown method: {method}")
        return

    try:
        result = METHODS[method](params)
        send_response(request_id, result=result)
    except Exception as e:
        log_debug(f"Error handling {method}: {traceback.format_exc()}")
        send_response(request_id, error=str(e))


def main():
    """Main loop: read JSON from stdin, process, write JSON to stdout."""
    log_debug("API server starting...")

    # Send ready signal
    send_response("__ready__", result={"status": "ready", "version": "1.0.0"})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            handle_request(request)
        except json.JSONDecodeError as e:
            log_debug(f"Invalid JSON: {e}")
            send_response("__error__", error=f"Invalid JSON: {e}")
        except Exception as e:
            log_debug(f"Unexpected error: {traceback.format_exc()}")
            send_response("__error__", error=f"Server error: {e}")


if __name__ == "__main__":
    main()
