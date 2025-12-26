#!/usr/bin/env python3
"""
Document Organizer UI - Streamlit interface for manual document classification

Run with: streamlit run ui.py

Workflow:
1. Run `python document_organizer.py --preprocess` to extract text + AI analysis
2. Open this UI to review and manually classify documents
3. Pick the category and file the document
"""

import streamlit as st
import json
import shutil
from pathlib import Path
from datetime import datetime
import base64

# Import icons
from icons import lucide_icon, icon_with_text, status_icon, file_type_icon

# Import from main module
from document_organizer import (
    JD_AREAS,
    SUPPORTED_FORMATS,
    extract_text_with_docling,
    extract_text_fallback,
    categorize_with_claude_code,
    categorize_with_keywords,
    organize_file,
    get_file_hash,
    load_processed_files,
    save_processed_files,
    mark_file_processed,
    get_analysis_path,
    has_analysis,
    load_analysis,
    save_analysis,
    preprocess_file,
    build_hash_index,
    load_hash_index,
    get_merged_jd_areas,
    get_area_range,
    DEFAULT_JD_INBOX,
    DEFAULT_JD_OUTPUT,
)

# Import settings management
from settings import get_settings, get_config_dir

# For thumbnail generation
from PIL import Image
import io
try:
    import fitz  # PyMuPDF for PDF thumbnails
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Page config
st.set_page_config(
    page_title="Document Organizer",
    page_icon=":material/folder:",
    layout="wide",
)

# Hand loading animation CSS (inspired by https://codepen.io/r4ms3s/pen/XJqeKB)
HAND_LOADING_CSS = """
<style>
.hand-loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
.hand-loading-text {
    margin-top: 15px;
    font-size: 14px;
    color: #666;
}
.loading {
    position: relative;
    width: 120px;
    height: 70px;
}
.finger {
    float: left;
    margin: 0 2px;
    width: 20px;
}
.finger-item {
    position: relative;
    width: 20px;
    height: 100%;
    border-radius: 10px 10px 5px 5px;
    background: #fff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.finger-item span {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    padding-top: 100%;
    border-radius: 50%;
    background: #4492f4;
}
.finger-item i {
    position: absolute;
    top: 37%;
    left: 50%;
    width: 2px;
    height: 30%;
    background: rgba(0,0,0,0.1);
    margin-left: -1px;
    border-radius: 1px;
}
.finger-1 { height: 48px; animation: finger-1 2s infinite ease-in-out; }
.finger-2 { height: 56px; animation: finger-2 2s infinite ease-in-out; }
.finger-3 { height: 52px; animation: finger-3 2s infinite ease-in-out; }
.finger-4 { height: 44px; animation: finger-4 2s infinite ease-in-out; }
.last-finger {
    position: absolute;
    bottom: 0;
    right: -12px;
    width: 24px;
    height: 32px;
}
.last-finger-item {
    position: relative;
    width: 24px;
    height: 100%;
    border-radius: 0 10px 10px 0;
    background: #fff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    animation: last-finger 2s infinite ease-in-out;
    transform-origin: left center;
}
.last-finger-item i {
    position: absolute;
    left: 40%;
    top: 50%;
    width: 40%;
    height: 2px;
    background: rgba(0,0,0,0.1);
    margin-top: -1px;
    border-radius: 1px;
}
@keyframes finger-1 {
    0%, 100% { transform: translateY(0); }
    20% { transform: translateY(-15px); }
    40% { transform: translateY(0); }
}
@keyframes finger-2 {
    0%, 100% { transform: translateY(0); }
    25% { transform: translateY(-18px); }
    50% { transform: translateY(0); }
}
@keyframes finger-3 {
    0%, 100% { transform: translateY(0); }
    30% { transform: translateY(-16px); }
    60% { transform: translateY(0); }
}
@keyframes finger-4 {
    0%, 100% { transform: translateY(0); }
    35% { transform: translateY(-12px); }
    70% { transform: translateY(0); }
}
@keyframes last-finger {
    0%, 100% { transform: rotate(0deg); }
    40% { transform: rotate(-20deg); }
    80% { transform: rotate(0deg); }
}
</style>
"""

HAND_LOADING_HTML = """
<div class="hand-loading-container">
    <div class="loading">
        <div class="finger finger-1">
            <div class="finger-item"><span></span><i></i></div>
        </div>
        <div class="finger finger-2">
            <div class="finger-item"><span></span><i></i></div>
        </div>
        <div class="finger finger-3">
            <div class="finger-item"><span></span><i></i></div>
        </div>
        <div class="finger finger-4">
            <div class="finger-item"><span></span><i></i></div>
        </div>
        <div class="last-finger">
            <div class="last-finger-item"><i></i></div>
        </div>
    </div>
    <div class="hand-loading-text">{text}</div>
</div>
"""

def show_hand_loading(text: str = "Loading..."):
    """Display animated hand loading indicator."""
    st.markdown(HAND_LOADING_CSS, unsafe_allow_html=True)
    st.markdown(HAND_LOADING_HTML.format(text=text), unsafe_allow_html=True)


# ==============================================================================
# TAG CHIPS & UI COMPONENTS
# ==============================================================================

# Color mapping for JD areas and common tags
TAG_COLORS = {
    # JD Areas
    "10-19 finance": "#27ae60",
    "20-29 medical": "#e74c3c",
    "30-39 legal": "#3498db",
    "40-49 work": "#9b59b6",
    "50-59 personal": "#f39c12",
    "00-09 system": "#7f8c8d",
    # Common tags
    "bank": "#27ae60",
    "tax": "#27ae60",
    "insurance": "#2ecc71",
    "receipt": "#1abc9c",
    "medical": "#e74c3c",
    "doctor": "#e74c3c",
    "hospital": "#c0392b",
    "prescription": "#e74c3c",
    "contract": "#3498db",
    "legal": "#3498db",
    "employment": "#9b59b6",
    "salary": "#9b59b6",
    "education": "#f39c12",
    "travel": "#f39c12",
}

TAG_CHIPS_CSS = """
<style>
.tag-container {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin: 4px 0;
}
.tag-chip {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    color: white;
    white-space: nowrap;
}
.tag-chip-small {
    padding: 1px 6px;
    font-size: 10px;
    border-radius: 8px;
}
/* Grid view styles */
.file-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 16px;
    padding: 8px;
}
.file-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px;
    background: #fafafa;
    cursor: pointer;
    transition: all 0.2s ease;
}
.file-card:hover {
    border-color: #4492f4;
    box-shadow: 0 2px 8px rgba(68, 146, 244, 0.2);
}
.file-card.selected {
    border-color: #4492f4;
    background: #e3f2fd;
}
.file-card-thumb {
    width: 100%;
    height: 120px;
    object-fit: cover;
    border-radius: 4px;
    background: #e0e0e0;
    display: flex;
    align-items: center;
    justify-content: center;
}
.file-card-name {
    font-size: 12px;
    font-weight: 500;
    margin-top: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.file-card-meta {
    font-size: 10px;
    color: #666;
    margin-top: 4px;
}
/* Breadcrumb styles */
.breadcrumb {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 14px;
    padding: 8px 0;
    flex-wrap: wrap;
}
.breadcrumb-item {
    color: #666;
    text-decoration: none;
    padding: 2px 6px;
    border-radius: 4px;
}
.breadcrumb-item:hover {
    background: #e0e0e0;
    color: #333;
}
.breadcrumb-item.current {
    color: #333;
    font-weight: 500;
}
.breadcrumb-sep {
    color: #999;
}
/* Destination preview */
.dest-preview {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}
.dest-preview-path {
    font-family: monospace;
    font-size: 13px;
    color: #495057;
    word-break: break-all;
}
.dest-preview-label {
    font-size: 11px;
    color: #6c757d;
    margin-bottom: 4px;
}
/* Icon header styles */
.icon-title {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 2rem;
    font-weight: 700;
    margin: 0.5rem 0 1rem 0;
}
.icon-subheader {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0.75rem 0 0.5rem 0;
}
.icon-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
/* File list item with icon */
.file-item-icon {
    display: inline-flex;
    align-items: center;
    gap: 8px;
}
.file-item-icon svg {
    flex-shrink: 0;
}
/* Gallery strip styles (Finder Gallery View) */
.gallery-strip-container {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 8px;
    margin: 8px 0;
}
.gallery-strip {
    display: flex;
    overflow-x: auto;
    gap: 8px;
    padding: 8px 4px;
    scroll-behavior: smooth;
}
.gallery-strip::-webkit-scrollbar {
    height: 6px;
}
.gallery-strip::-webkit-scrollbar-track {
    background: #e0e0e0;
    border-radius: 3px;
}
.gallery-strip::-webkit-scrollbar-thumb {
    background: #bbb;
    border-radius: 3px;
}
.gallery-strip::-webkit-scrollbar-thumb:hover {
    background: #999;
}
.gallery-card {
    flex: 0 0 auto;
    width: 130px;
    text-align: center;
    padding: 6px;
    border-radius: 6px;
    border: 2px solid transparent;
    transition: all 0.15s ease;
    cursor: pointer;
    background: white;
}
.gallery-card:hover {
    background: #e8f4fd;
    border-color: #90caf9;
}
.gallery-card.selected {
    border-color: #4492f4;
    background: #e3f2fd;
}
.gallery-card.current {
    border-color: #1976d2;
    background: #bbdefb;
}
.gallery-card-thumb {
    width: 130px;
    height: 100px;
    object-fit: cover;
    border-radius: 4px;
    background: #e0e0e0;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto;
}
.gallery-card-thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 4px;
}
.gallery-card-name {
    font-size: 11px;
    margin-top: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #333;
}
.gallery-card-status {
    font-size: 9px;
    color: #666;
    margin-top: 2px;
}
.gallery-card-checkbox {
    position: absolute;
    top: 2px;
    left: 2px;
}
/* Actions toolbar */
.actions-toolbar {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}
/* Classification section */
.classification-section {
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px;
    margin-top: 12px;
}
.classification-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 8px;
}
.classification-item {
    font-size: 13px;
}
.classification-item strong {
    color: #666;
}
</style>
"""


def get_tag_color(tag: str) -> str:
    """Get color for a tag based on its content."""
    tag_lower = tag.lower()
    # Check exact match first
    if tag_lower in TAG_COLORS:
        return TAG_COLORS[tag_lower]
    # Check partial match
    for key, color in TAG_COLORS.items():
        if key in tag_lower or tag_lower in key:
            return color
    # Default color
    return "#95a5a6"


def render_tag_chips(tags: list, small: bool = False) -> str:
    """Render tags as colored chips. Returns HTML string."""
    if not tags:
        return ""

    size_class = "tag-chip-small" if small else ""
    chips = []
    for tag in tags[:8]:  # Limit to 8 tags
        color = get_tag_color(tag)
        chips.append(f'<span class="tag-chip {size_class}" style="background:{color}">{tag}</span>')

    return f'<div class="tag-container">{"".join(chips)}</div>'


def render_category_chip(area: str, category: str) -> str:
    """Render JD area/category as a chip."""
    area_lower = area.lower() if area else ""
    color = TAG_COLORS.get(area_lower, "#95a5a6")
    cat_short = category.split(" ", 1)[1] if category and " " in category else category
    return f'<span class="tag-chip" style="background:{color}">{cat_short}</span>'


def icon_title(icon_name: str, text: str, size: int = 28) -> None:
    """Render a page title with a Lucide icon."""
    st.markdown(TAG_CHIPS_CSS, unsafe_allow_html=True)
    icon_svg = lucide_icon(icon_name, size=size)
    st.markdown(f'<div class="icon-title">{icon_svg}<span>{text}</span></div>', unsafe_allow_html=True)


def icon_subheader(icon_name: str, text: str, size: int = 22) -> None:
    """Render a subheader with a Lucide icon."""
    st.markdown(TAG_CHIPS_CSS, unsafe_allow_html=True)
    icon_svg = lucide_icon(icon_name, size=size)
    st.markdown(f'<div class="icon-subheader">{icon_svg}<span>{text}</span></div>', unsafe_allow_html=True)


def icon_label(icon_name: str, text: str, size: int = 16) -> str:
    """Return HTML for an inline icon + text label."""
    icon_svg = lucide_icon(icon_name, size=size)
    return f'<span class="icon-label">{icon_svg}<span>{text}</span></span>'


# ==============================================================================
# THUMBNAIL GENERATION
# ==============================================================================

@st.cache_data(ttl=3600)
def generate_thumbnail(file_path: str, size: tuple = (400, 400)) -> bytes | None:
    """Generate a high-quality thumbnail for a file. Returns image data as bytes.

    Optimized for text-heavy scanned documents with sharpening for better readability.

    Args:
        file_path: Path to the file
        size: Maximum size for thumbnail generation (default 400x400 for sharp display)
    """
    from PIL import ImageFilter, ImageEnhance

    path = Path(file_path)
    suffix = path.suffix.lower()

    def sharpen_for_text(img: Image.Image) -> Image.Image:
        """Apply light sharpening to improve text readability in thumbnails."""
        # UnsharpMask: radius=1, percent=120, threshold=2
        # This sharpens text edges without being too harsh on photos
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=2))
        # Slight contrast boost to make text pop
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)
        return img

    try:
        if suffix in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            # Image files
            img = Image.open(path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            # Apply sharpening for text clarity
            img = sharpen_for_text(img)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            return buffer.getvalue()

        elif suffix == '.pdf' and HAS_PYMUPDF:
            # PDF files - use first page with high resolution rendering
            doc = fitz.open(str(path))
            if len(doc) > 0:
                page = doc[0]
                # Render at 2.0x resolution for sharp text in thumbnails
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                # Apply sharpening for text clarity
                img = sharpen_for_text(img)
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=95)
                doc.close()
                return buffer.getvalue()
            doc.close()

        elif suffix == '.tiff':
            img = Image.open(path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            # Apply sharpening for text clarity
            img = sharpen_for_text(img)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            return buffer.getvalue()

    except Exception as e:
        pass

    return None


def get_file_icon(suffix: str, size: int = 20) -> str:
    """Get a Lucide icon for a file type. Returns HTML SVG string."""
    return file_type_icon(suffix, size=size)


# ==============================================================================
# BREADCRUMB NAVIGATION
# ==============================================================================

def render_breadcrumb(current_path: Path, base_path: Path) -> None:
    """Render clickable breadcrumb navigation."""
    try:
        relative = current_path.relative_to(base_path)
        parts = list(relative.parts)
    except ValueError:
        parts = []

    # Build breadcrumb HTML
    st.markdown(TAG_CHIPS_CSS, unsafe_allow_html=True)

    crumbs = [f'<span class="breadcrumb-item" title="{base_path}">{base_path.name}</span>']

    for i, part in enumerate(parts):
        crumbs.append('<span class="breadcrumb-sep">/</span>')
        is_current = (i == len(parts) - 1)
        class_name = "breadcrumb-item current" if is_current else "breadcrumb-item"
        crumbs.append(f'<span class="{class_name}">{part}</span>')

    st.markdown(f'<div class="breadcrumb">{"".join(crumbs)}</div>', unsafe_allow_html=True)


# ==============================================================================
# DESTINATION PREVIEW
# ==============================================================================

def render_destination_preview(area: str, category: str, issuer: str, doc_type: str,
                                date: str, output_dir: str) -> None:
    """Show preview of where the file will be organized."""
    st.markdown(TAG_CHIPS_CSS, unsafe_allow_html=True)

    # Build the destination path preview
    year = date[:4] if date and len(date) >= 4 else datetime.now().strftime("%Y")

    # Build filename preview
    parts = []
    if issuer:
        parts.append(issuer)
    if doc_type:
        parts.append(doc_type)
    descriptor = " ".join(parts) if parts else "Document"

    filename = f"XX.XX {descriptor} {year}.pdf"
    full_path = f"{Path(output_dir).name}/{area}/{category}/{filename}"

    html = f'''
    <div class="dest-preview">
        <div class="dest-preview-label">{lucide_icon("map-pin", size=14)} Destination Preview</div>
        <div class="dest-preview-path">{full_path}</div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)


from contextlib import contextmanager
import subprocess
import platform


def reveal_in_file_manager(file_path: Path):
    """Open the system file manager and select/highlight the given file.

    Works on macOS, Windows, and Linux.
    """
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", "-R", str(file_path)], check=False)
        elif system == "Windows":
            subprocess.run(["explorer", "/select,", str(file_path)], check=False)
        else:  # Linux and others
            # xdg-open opens the parent folder (can't select specific file)
            subprocess.run(["xdg-open", str(file_path.parent)], check=False)
    except (OSError, subprocess.SubprocessError):
        pass  # Silently fail if file manager can't be opened


def get_file_manager_name() -> str:
    """Get the name of the system file manager for button labels."""
    system = platform.system()
    if system == "Darwin":
        return "Finder"
    elif system == "Windows":
        return "Explorer"
    else:
        return "Files"


@contextmanager
def hand_spinner(text: str = "Loading..."):
    """Context manager for hand loading animation (replaces st.spinner)."""
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(HAND_LOADING_CSS, unsafe_allow_html=True)
        st.markdown(HAND_LOADING_HTML.format(text=text), unsafe_allow_html=True)
    try:
        yield
    finally:
        placeholder.empty()


# ==============================================================================
# GALLERY VIEW COMPONENTS
# ==============================================================================

def render_actions_toolbar(
    files: list,
    current_file: Path | None,
    analysis: dict | None,
    selection_mode: bool,
    selected_files: set,
    output_dir: str,
    inbox_dir: str
) -> tuple[str | None, str | None, str | None]:
    """Render the full-width actions toolbar.

    Returns (action, area, category) where action is the button clicked or None.
    """
    areas, area_categories = get_areas_and_categories(output_dir)

    # Determine if actions should be enabled
    if selection_mode:
        has_selection = len(selected_files) > 0
        selection_count = len(selected_files)
    else:
        has_selection = current_file is not None and current_file.exists()
        selection_count = 1 if has_selection else 0

    # Pre-fill area/category from analysis
    default_area_idx = 0
    default_cat_idx = 0
    if analysis:
        ai_area = analysis.get('jd_area', '')
        if ai_area in areas:
            default_area_idx = areas.index(ai_area)

    # Actions toolbar row
    col_area, col_cat, col_move, col_reanalyze, col_delete, col_reveal = st.columns([2, 2, 1, 1, 1, 1])

    with col_area:
        selected_area = st.selectbox(
            "Area",
            areas,
            index=default_area_idx,
            key="toolbar_area",
            disabled=not has_selection,
            label_visibility="collapsed"
        )

    with col_cat:
        categories = area_categories.get(selected_area, [])
        if analysis:
            ai_cat = analysis.get('jd_category', '')
            if ai_cat in categories:
                default_cat_idx = categories.index(ai_cat)
        selected_category = st.selectbox(
            "Category",
            categories,
            index=default_cat_idx,
            key="toolbar_category",
            disabled=not has_selection,
            label_visibility="collapsed"
        )

    action = None

    with col_move:
        if st.button("Move", type="primary", use_container_width=True, disabled=not has_selection):
            action = "move"

    with col_reanalyze:
        if st.button("Reanalyze", use_container_width=True, disabled=not has_selection):
            action = "reanalyze"

    with col_delete:
        if st.button("Delete", use_container_width=True, disabled=not has_selection):
            action = "delete"

    with col_reveal:
        fm_name = get_file_manager_name()
        if st.button("Reveal", use_container_width=True, disabled=not has_selection, help=f"Show in {fm_name}"):
            action = "reveal"

    return action, selected_area, selected_category


def render_gallery_strip(
    files: list,
    current_idx: int,
    selection_mode: bool,
    selected_files: set
) -> tuple[int | None, bool | None]:
    """Render horizontal gallery strip with exactly 7 visible thumbnails.

    Shows 7 files at a time with the current file centered when possible.
    Left/right arrows scroll by 1 file at a time.

    Returns (clicked_idx, selection_mode_changed) where:
    - clicked_idx is the index of clicked file or None
    - selection_mode_changed is True if toggled, False if not, None if unchanged
    """
    st.markdown(TAG_CHIPS_CSS, unsafe_allow_html=True)

    clicked_idx = None
    mode_changed = None

    # Constants for pagination
    VISIBLE_COUNT = 7

    # Calculate the window of visible files (center current file when possible)
    total_files = len(files)

    if total_files <= VISIBLE_COUNT:
        # Show all files if we have 7 or fewer
        start_idx = 0
        end_idx = total_files
    else:
        # Center the current file in the visible window
        half_visible = VISIBLE_COUNT // 2  # 3 files on each side

        # Calculate ideal start position (current file centered)
        start_idx = current_idx - half_visible

        # Clamp to valid range
        if start_idx < 0:
            start_idx = 0
        elif start_idx > total_files - VISIBLE_COUNT:
            start_idx = total_files - VISIBLE_COUNT

        end_idx = start_idx + VISIBLE_COUNT

    # Header row: Select/Done + navigation arrows + file count
    col_select, col_prev, col_next, col_count = st.columns([1, 0.5, 0.5, 3])

    with col_select:
        if selection_mode:
            if st.button("Done", type="primary", use_container_width=True, key="gallery_done"):
                mode_changed = False  # Exit selection mode
        else:
            if st.button("Select", use_container_width=True, key="gallery_select"):
                mode_changed = True  # Enter selection mode

    with col_prev:
        # Can scroll left if current file is not the first
        can_scroll_left = current_idx > 0
        if st.button("◀", use_container_width=True, disabled=not can_scroll_left, key="gallery_prev"):
            clicked_idx = current_idx - 1

    with col_next:
        # Can scroll right if current file is not the last
        can_scroll_right = current_idx < total_files - 1
        if st.button("▶", use_container_width=True, disabled=not can_scroll_right, key="gallery_next"):
            clicked_idx = current_idx + 1

    with col_count:
        if selection_mode and selected_files:
            st.caption(f"**{len(selected_files)}** selected of {total_files} files")
        else:
            st.caption(f"**{current_idx + 1}** of {total_files} files")

    # Selection controls in selection mode
    if selection_mode:
        col_all, col_none = st.columns([1, 1])
        with col_all:
            if st.button("Select All", use_container_width=True, key="gallery_select_all"):
                st.session_state.selected_files = {str(f) for f, _, _ in files}
                st.session_state.checkbox_key_version += 1
                st.rerun()
        with col_none:
            if st.button("Clear", use_container_width=True, key="gallery_clear"):
                st.session_state.selected_files = set()
                st.session_state.checkbox_key_version += 1
                st.rerun()

    # Get the visible slice of files
    visible_files = files[start_idx:end_idx]

    # Create the gallery using exactly 7 columns (or fewer if less files)
    if visible_files:
        cols = st.columns(len(visible_files))

        for col_idx, (file, analyzed, analysis) in enumerate(visible_files):
            # Calculate the actual file index in the full list
            actual_idx = start_idx + col_idx

            with cols[col_idx]:
                is_current = (actual_idx == current_idx)
                is_selected = str(file) in selected_files

                # Card container with styling
                card_classes = "gallery-card"
                if is_current:
                    card_classes += " current"
                if is_selected:
                    card_classes += " selected"

                # Thumbnail - use higher resolution for sharp display
                thumb = generate_thumbnail(str(file), size=(400, 400))
                if thumb:
                    st.image(thumb, use_container_width=True)
                else:
                    icon = get_file_icon(file.suffix, size=48)
                    st.markdown(
                        f'<div class="gallery-card-thumb">{icon}</div>',
                        unsafe_allow_html=True
                    )

                # Status indicator
                status = "✓" if analyzed else "..."

                # File button - different behavior based on mode
                btn_type = "primary" if is_current else "secondary"

                if selection_mode:
                    # In selection mode: checkbox + click to toggle
                    cb_key = f"gal_sel_{actual_idx}_v{st.session_state.checkbox_key_version}"
                    checked = st.checkbox(
                        file.name[:12],
                        value=is_selected,
                        key=cb_key,
                        label_visibility="collapsed"
                    )
                    if checked and str(file) not in st.session_state.selected_files:
                        st.session_state.selected_files.add(str(file))
                        st.session_state.last_selected_file = file
                    elif not checked and str(file) in st.session_state.selected_files:
                        st.session_state.selected_files.discard(str(file))

                    # Also make thumbnail clickable
                    if st.button(file.name[:12], key=f"gal_btn_{actual_idx}", use_container_width=True):
                        # Toggle selection and set as preview
                        if str(file) in st.session_state.selected_files:
                            st.session_state.selected_files.discard(str(file))
                        else:
                            st.session_state.selected_files.add(str(file))
                        st.session_state.last_selected_file = file
                        st.session_state.checkbox_key_version += 1
                        st.rerun()
                else:
                    # In browse mode: click to select for preview
                    if st.button(file.name[:12], key=f"gal_btn_{actual_idx}", use_container_width=True,
                                type=btn_type if is_current else "secondary"):
                        clicked_idx = actual_idx

    return clicked_idx, mode_changed


def render_preview(file_path: Path | None, extracted_text: str = "") -> None:
    """Render the large preview section."""
    if file_path is None:
        st.info("Select a file from the gallery above to preview it")
        return

    if not file_path.exists():
        st.error("File no longer exists. It may have been moved or deleted.")
        return

    # Preview tabs
    tab1, tab2 = st.tabs(["Preview", "Extracted Text"])

    with tab1:
        suffix = file_path.suffix.lower()
        if suffix == '.pdf':
            display_pdf(file_path)
        elif suffix in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
            display_image(file_path)
        else:
            st.info(f"Preview not available for {suffix} files. Check 'Extracted Text' tab.")

    with tab2:
        if not extracted_text:
            st.warning("No extracted text available. Click 'Reanalyze' to extract text.")
        else:
            # Use file path in key to ensure text updates when file changes
            text_key = f"preview_text_{hash(str(file_path))}"
            st.text_area("Extracted Text", extracted_text, height=400, disabled=True, key=text_key)


def render_classification(analysis: dict | None, file_path: Path | None) -> None:
    """Render classification/AI analysis section below preview."""
    if not analysis:
        if file_path:
            st.warning("No analysis available. Click 'Reanalyze' to process this file.")
        return

    # Compact metadata row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        issuer = analysis.get('issuer', 'Unknown') or 'Unknown'
        st.markdown(f"**Issuer:** {issuer}")

    with col2:
        doc_type = analysis.get('document_type', 'Unknown') or 'Unknown'
        st.markdown(f"**Type:** {doc_type}")

    with col3:
        date = analysis.get('date_mentioned', 'N/A') or 'N/A'
        st.markdown(f"**Date:** {date}")

    with col4:
        confidence = analysis.get('confidence', 'Unknown') or 'Unknown'
        st.markdown(f"**Confidence:** {confidence}")

    # AI suggested category
    ai_area = analysis.get('jd_area', '')
    ai_cat = analysis.get('jd_category', '')
    if ai_area and ai_cat:
        st.markdown(f"**Suggested:** {ai_area} → {ai_cat}")

    # Tags
    tags = analysis.get('tags', [])
    if tags:
        st.markdown(render_tag_chips(tags), unsafe_allow_html=True)

    # Summary (collapsible)
    summary = analysis.get('summary', '')
    if summary:
        with st.expander("Summary", expanded=False):
            st.write(summary)


# Initialize session state
if "current_file" not in st.session_state:
    st.session_state.current_file = None
if "current_file_idx" not in st.session_state:
    st.session_state.current_file_idx = 0
if "processed_count" not in st.session_state:
    st.session_state.processed_count = 0
if "selected_files" not in st.session_state:
    st.session_state.selected_files = set()
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "search_field" not in st.session_state:
    st.session_state.search_field = "all"
if "browse_mode" not in st.session_state:
    st.session_state.browse_mode = False
if "browse_folder" not in st.session_state:
    st.session_state.browse_folder = ""
if "browse_recursive" not in st.session_state:
    st.session_state.browse_recursive = True
if "checkbox_key_version" not in st.session_state:
    st.session_state.checkbox_key_version = 0
if "recent_files" not in st.session_state:
    st.session_state.recent_files = []  # Track recently processed files
if "nav_history" not in st.session_state:
    st.session_state.nav_history = []  # Navigation history for back/forward
if "nav_history_idx" not in st.session_state:
    st.session_state.nav_history_idx = -1  # Current position in history
if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = False  # iOS-style: False = browse mode, True = select mode
if "last_selected_file" not in st.session_state:
    st.session_state.last_selected_file = None  # Track last clicked file in select mode for preview


def get_inbox_files(inbox_dir: str) -> list[tuple[Path, bool, dict | None]]:
    """Get list of files in inbox with their analysis status and data.

    Recursively scans subfolders to find all documents.
    Returns list of (file_path, has_analysis, analysis_data) tuples.
    """
    inbox = Path(inbox_dir)
    if not inbox.exists():
        return []

    files = []
    # Use rglob to recursively find all files in subfolders
    for f in sorted(inbox.rglob('*')):
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS:
            analysis = load_analysis(str(f))
            files.append((f, analysis is not None, analysis))
    return files


def get_folder_files(folder_path: str, recursive: bool = True) -> list[tuple[Path, bool, dict | None]]:
    """Get list of files in any folder with their metadata status.

    Loads metadata from .meta.json sidecar files (for organized files).
    Returns list of (file_path, has_metadata, metadata) tuples.
    """
    folder = Path(folder_path)
    if not folder.exists():
        return []

    files = []
    file_iter = folder.rglob("*") if recursive else folder.iterdir()

    for f in sorted(file_iter):
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS:
            # Try .meta.json first (organized files)
            meta_path = f.with_suffix(f.suffix + ".meta.json")
            metadata = None
            if meta_path.exists():
                try:
                    with open(meta_path, 'r') as mf:
                        metadata = json.load(mf)
                except (json.JSONDecodeError, IOError):
                    pass

            # Fall back to load_analysis (checks .meta.json)
            if metadata is None:
                metadata = load_analysis(str(f))

            files.append((f, metadata is not None, metadata))

    return files


def filter_files(files: list, query: str, field: str) -> list:
    """Filter files based on search query and field."""
    if not query:
        return files

    query_lower = query.lower()
    filtered = []

    for file_path, has_anal, analysis in files:
        match = False

        if field == "all" or field == "filename":
            if query_lower in file_path.name.lower():
                match = True

        if analysis and not match:
            if field == "all" or field == "issuer":
                issuer = analysis.get("issuer", "") or ""
                if query_lower in issuer.lower():
                    match = True

            if field == "all" or field == "document_type":
                doc_type = analysis.get("document_type", "") or ""
                if query_lower in doc_type.lower():
                    match = True

            if field == "all" or field == "summary":
                summary = analysis.get("summary", "") or ""
                if query_lower in summary.lower():
                    match = True

            if field == "all" or field == "tags":
                tags = analysis.get("tags", []) or []
                if any(query_lower in t.lower() for t in tags):
                    match = True

            if field == "all" or field == "category":
                area = analysis.get("jd_area", "") or ""
                cat = analysis.get("jd_category", "") or ""
                if query_lower in area.lower() or query_lower in cat.lower():
                    match = True

            if field == "all" or field == "text":
                text = analysis.get("extracted_text", "") or ""
                if query_lower in text.lower():
                    match = True

        if match:
            filtered.append((file_path, has_anal, analysis))

    return filtered


def save_uploaded_files(uploaded_files, inbox_dir: str) -> int:
    """Save uploaded files to inbox, handling duplicate filenames.

    Returns the number of files successfully uploaded.
    """
    if not uploaded_files:
        return 0

    inbox_path = Path(inbox_dir)
    inbox_path.mkdir(parents=True, exist_ok=True)

    uploaded_count = 0
    for uploaded_file in uploaded_files:
        dest = inbox_path / uploaded_file.name
        # Handle duplicate filenames with counter suffix
        counter = 1
        while dest.exists():
            stem = Path(uploaded_file.name).stem
            suffix = Path(uploaded_file.name).suffix
            dest = inbox_path / f"{stem}_{counter}{suffix}"
            counter += 1
        with open(dest, "wb") as f:
            f.write(uploaded_file.getbuffer())
        uploaded_count += 1

    return uploaded_count


def display_pdf(file_path: Path):
    """Display PDF in iframe."""
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Could not display PDF: {e}")


def display_image(file_path: Path):
    """Display image."""
    st.image(str(file_path), width="stretch")


def get_areas_and_categories(output_dir: str | None = None):
    """Get list of areas and their categories for dropdowns.

    Merges the predefined JD_AREAS with any user-created folders discovered
    on the filesystem. User-created folders take precedence for categories
    (i.e., if user renamed a category, the new name is used).

    Args:
        output_dir: Optional path to scan for user-created folders.
                   If None, only returns predefined JD_AREAS.

    Returns:
        Tuple of (areas_list, area_categories_dict)
    """
    # Get merged JD areas (predefined + user-created from filesystem)
    merged_areas = get_merged_jd_areas(output_dir)

    # Convert to list format for dropdowns
    areas = []
    area_categories = {}

    for area, categories in merged_areas.items():
        if area == "00-09 System":
            # Only include Uncategorized from System area
            areas.append(area)
            area_categories[area] = ["09 Uncategorized"]
        elif area != "90-99 Archive":
            areas.append(area)
            area_categories[area] = list(categories.keys())

    # Sort areas by their numeric prefix
    areas = sorted(areas, key=lambda x: get_area_range(x) or (99, 99))

    return areas, area_categories


def delete_analysis_file(file_path: Path):
    """Delete the analysis JSON file for a document."""
    analysis_path = get_analysis_path(str(file_path))
    if analysis_path.exists():
        analysis_path.unlink()


def reanalyze_file(file_path: Path, skip_if_has_text: bool = True, progress_callback=None) -> bool:
    """Reanalyze a file to extract text.

    For organized files (with .meta.json), updates the metadata file
    with the newly extracted text.

    Args:
        file_path: Path to the file to reanalyze
        skip_if_has_text: If True, skip files that already have extracted_text
        progress_callback: Optional callback function(step: str) to report progress

    Returns:
        True if file was processed, False if skipped
    """
    meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")

    # Check if we should skip this file (already has extracted text)
    if skip_if_has_text and meta_path.exists():
        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)
            existing_text = metadata.get("extracted_text", "").strip()
            if existing_text:
                print(f"  ⏭️  Skipping {file_path.name} - already has {len(existing_text)} chars of text")
                return False  # Skip - already has extracted text
        except (json.JSONDecodeError, IOError):
            pass  # Continue with reanalysis if we can't read the file

    print(f"  🔄 Reanalyzing {file_path.name}...")

    # Clean up orphaned analysis files in the same folder first
    cleanup_orphaned_analysis_files(file_path.parent)
    delete_analysis_file(file_path)
    result = preprocess_file(str(file_path), progress_callback=progress_callback)

    # Check if preprocess succeeded
    if not result.get("success"):
        print(f"  ❌ Preprocess failed for {file_path.name}: {result.get('error', 'unknown')}")
        return True  # Return True because we tried (not skipped)

    # If this is an organized file (has .meta.json), update it with extracted text
    analysis_path = get_analysis_path(str(file_path))

    if meta_path.exists() and analysis_path.exists():
        try:
            # Load the new analysis with extracted text
            with open(analysis_path, 'r') as f:
                analysis = json.load(f)

            # Load existing metadata
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            # Only update extracted_text - preserve all other manually curated fields
            new_text = analysis.get("extracted_text", "")
            metadata["extracted_text"] = new_text
            print(f"  ✅ Updated {file_path.name} with {len(new_text)} chars of text")

            # Save updated metadata
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # Clean up the analysis file since metadata is now updated
            analysis_path.unlink()
        except (json.JSONDecodeError, IOError) as e:
            print(f"  ❌ Failed to update metadata for {file_path.name}: {e}")
    elif meta_path.exists():
        print(f"  ⚠️  No meta.json created for {file_path.name}")
    else:
        print(f"  ℹ️  No meta.json for {file_path.name} (inbox file)")

    return True


def cleanup_orphaned_analysis_files(folder: Path) -> int:
    """Remove orphaned .meta.json files in a folder.

    An orphaned meta file is one where no matching document exists
    (e.g., the document was deleted or renamed).

    Returns the number of deleted files.
    """
    if not folder.exists():
        return 0

    # Find all meta files in the folder
    meta_files = list(folder.glob("*.meta.json"))
    if not meta_files:
        return 0

    # Find orphaned meta files (no matching document)
    orphaned = []
    for meta_path in meta_files:
        # Get the original document name by removing .meta.json suffix
        doc_name = meta_path.name.replace(".meta.json", "")
        doc_path = folder / doc_name
        if not doc_path.exists():
            orphaned.append(meta_path)

    if not orphaned:
        return 0

    # Delete all orphaned meta files
    deleted = 0
    for orphan in orphaned:
        orphan.unlink()
        deleted += 1

    return deleted


def main():
    icon_title("folder-check", "Document Organizer")

    # Get settings
    settings = get_settings()

    # Sidebar for settings
    with st.sidebar:
        # Use settings for directories (read-only display, edit in Settings page)
        output_dir = settings.output_dir
        default_inbox = settings.inbox_dir

        st.caption(f"Library: `{Path(output_dir).name}`")

        st.divider()

        # Source mode toggle
        icon_subheader("folder-tree", "File Source")
        source_mode = st.radio(
            "Select source",
            ["Inbox", "Browse Folder"],
            index=1 if st.session_state.browse_mode else 0,
            key="source_mode_radio",
            horizontal=True
        )
        st.session_state.browse_mode = (source_mode == "Browse Folder")

        if st.session_state.browse_mode:
            # Browse folder mode - use browse_folder_input as source of truth
            if "browse_folder_input" not in st.session_state:
                st.session_state.browse_folder_input = st.session_state.browse_folder or output_dir

            browse_folder = st.text_input(
                "Folder path",
                key="browse_folder_input",
                placeholder="/path/to/folder"
            )

            current_folder = browse_folder or output_dir
            current_path = Path(current_folder)

            # Navigation helper functions
            def navigate_to(path: str, add_to_history: bool = True):
                """Navigate to a path, optionally adding to history."""
                if add_to_history:
                    current = st.session_state.browse_folder_input or output_dir
                    # Only add if different from current location
                    if current != path:
                        # Truncate forward history when navigating to new location
                        idx = st.session_state.nav_history_idx
                        st.session_state.nav_history = st.session_state.nav_history[:idx + 1]
                        st.session_state.nav_history.append(current)
                        st.session_state.nav_history_idx = len(st.session_state.nav_history) - 1
                        # Limit history size
                        if len(st.session_state.nav_history) > 50:
                            st.session_state.nav_history = st.session_state.nav_history[-50:]
                            st.session_state.nav_history_idx = len(st.session_state.nav_history) - 1
                st.session_state.browse_folder_input = path

            def go_back():
                """Go to previous location in history."""
                if st.session_state.nav_history_idx >= 0:
                    # Save current location for forward
                    current = st.session_state.browse_folder_input or output_dir
                    idx = st.session_state.nav_history_idx
                    # If we're not already in forward territory, save current
                    if idx == len(st.session_state.nav_history) - 1:
                        st.session_state.nav_history.append(current)
                    prev_path = st.session_state.nav_history[idx]
                    st.session_state.nav_history_idx -= 1
                    st.session_state.browse_folder_input = prev_path

            def go_forward():
                """Go to next location in history."""
                if st.session_state.nav_history_idx < len(st.session_state.nav_history) - 1:
                    st.session_state.nav_history_idx += 1
                    next_path = st.session_state.nav_history[st.session_state.nav_history_idx]
                    st.session_state.browse_folder_input = next_path

            def go_up():
                """Go to parent folder."""
                if current_path.parent.exists():
                    navigate_to(str(current_path.parent))

            def go_down():
                """Go into first subfolder."""
                subfolders = sorted([d for d in current_path.iterdir() if d.is_dir()])
                if subfolders:
                    navigate_to(str(subfolders[0]))

            # Navigation buttons row
            can_go_back = st.session_state.nav_history_idx >= 0
            can_go_forward = st.session_state.nav_history_idx < len(st.session_state.nav_history) - 1
            can_go_up = current_path != Path(output_dir) and current_path.parent.exists()
            can_go_down = current_path.exists() and any(d.is_dir() for d in current_path.iterdir()) if current_path.exists() else False

            nav_cols = st.columns(4)
            with nav_cols[0]:
                st.button("◀", key="nav_back", on_click=go_back, disabled=not can_go_back, help="Back", use_container_width=True)
            with nav_cols[1]:
                st.button("▶", key="nav_forward", on_click=go_forward, disabled=not can_go_forward, help="Forward", use_container_width=True)
            with nav_cols[2]:
                st.button("▲", key="nav_up", on_click=go_up, disabled=not can_go_up, help="Parent folder", use_container_width=True)
            with nav_cols[3]:
                st.button("▼", key="nav_down", on_click=go_down, disabled=not can_go_down, help="Into subfolder", use_container_width=True)

            # Subfolder dropdown navigation
            if current_path.exists() and current_path.is_dir():
                subfolders = sorted([d.name for d in current_path.iterdir() if d.is_dir()])
                if subfolders:
                    options = ["(current folder)"] + subfolders

                    def navigate_subfolder():
                        selected = st.session_state.subfolder_select
                        if selected != "(current folder)":
                            new_path = str(current_path / selected)
                            navigate_to(new_path)

                    st.selectbox(
                        "Navigate to subfolder",
                        options,
                        index=0,
                        key="subfolder_select",
                        on_change=navigate_subfolder
                    )

            st.session_state.browse_recursive = st.checkbox(
                "Include subfolders",
                value=st.session_state.browse_recursive,
                key="browse_recursive_cb"
            )
            # Get files from browse folder (use session state)
            all_files = get_folder_files(current_folder, st.session_state.browse_recursive)
            analyzed = sum(1 for _, has, _ in all_files if has)
            inbox_dir = current_folder  # Use for compatibility
        else:
            # Inbox mode - use settings
            inbox_dir = default_inbox
            st.caption(f"Inbox: `{Path(inbox_dir).name}`")
            all_files = get_inbox_files(inbox_dir)
            analyzed = sum(1 for _, has, _ in all_files if has)

        st.divider()

        # Stats
        st.metric("Files Found", len(all_files))
        st.metric("With Metadata", f"{analyzed}/{len(all_files)}")
        st.metric("Processed This Session", st.session_state.processed_count)

        st.divider()

        # Analyze buttons - only for inbox mode
        if not st.session_state.browse_mode:
            if st.button("Analyze All New Files", width="stretch"):
                # Get files that need analysis
                files_to_analyze = [(f, a, d) for f, a, d in all_files if not a]
                total = len(files_to_analyze)

                if total == 0:
                    st.info("All files already analyzed!")
                else:
                    # Create progress container
                    progress_container = st.empty()

                    for idx, (file_path, _, _) in enumerate(files_to_analyze):
                        processed = idx
                        remaining = total - idx

                        # Update progress display
                        with progress_container.container():
                            st.markdown(HAND_LOADING_CSS, unsafe_allow_html=True)
                            progress_html = f"""
                            <div class="hand-loading-container">
                                <div class="loading">
                                    <div class="finger finger-1"><div class="finger-item"><span></span><i></i></div></div>
                                    <div class="finger finger-2"><div class="finger-item"><span></span><i></i></div></div>
                                    <div class="finger finger-3"><div class="finger-item"><span></span><i></i></div></div>
                                    <div class="finger finger-4"><div class="finger-item"><span></span><i></i></div></div>
                                    <div class="last-finger"><div class="last-finger-item"><i></i></div></div>
                                </div>
                                <div class="hand-loading-text">
                                    <strong>Processing:</strong> {file_path.name[:40]}{'...' if len(file_path.name) > 40 else ''}<br>
                                    <strong>Completed:</strong> {processed} / {total}<br>
                                    <strong>Remaining:</strong> {remaining}
                                </div>
                            </div>
                            """
                            st.markdown(progress_html, unsafe_allow_html=True)

                        preprocess_file(str(file_path))

                    progress_container.empty()
                    st.success(f"Analyzed {total} files!")
                st.rerun()
            st.divider()

        if st.button("Refresh", use_container_width=True):
            st.rerun()

        st.divider()

        # File upload in sidebar (always available)
        with st.expander("Upload Files"):
            uploaded_files = st.file_uploader(
                "Drop files here",
                accept_multiple_files=True,
                type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'docx', 'txt'],
                key="sidebar_uploader",
                label_visibility="collapsed"
            )
            uploaded_count = save_uploaded_files(uploaded_files, inbox_dir)
            if uploaded_count:
                st.success(f"Uploaded {uploaded_count} files!")
                st.rerun()

        st.divider()

        # Navigation section - Documents/Settings
        icon_subheader("navigation", "Navigation")
        page = st.radio(
            "Go to",
            ["Documents", "Settings"],
            index=0 if st.session_state.nav_page == "Documents" else 1,
            key="nav_radio",
            horizontal=True,
            label_visibility="collapsed"
        )
        if page != st.session_state.nav_page:
            st.session_state.nav_page = page
            st.rerun()

    # Search section
    icon_subheader("search", "Search")
    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        search_query = st.text_input("Search", value=st.session_state.search_query,
                                      placeholder="Search files by metadata...", label_visibility="collapsed")
        st.session_state.search_query = search_query
    with col_search2:
        search_field = st.selectbox("Field",
                                     ["all", "filename", "issuer", "document_type", "summary", "tags", "category", "text"],
                                     index=0, label_visibility="collapsed")
        st.session_state.search_field = search_field

    # Get and filter files (reuse already fetched files from sidebar)
    # all_files was already set in sidebar based on browse_mode
    files = filter_files(all_files, search_query, search_field)

    if not files:
        if search_query:
            st.info(f"No files match '{search_query}' in {search_field}")
        else:
            st.info("No files in inbox. Upload documents below or drop them into the inbox folder.")

            # Drag & drop file uploader
            uploaded_files = st.file_uploader(
                "Drop files here to upload",
                accept_multiple_files=True,
                type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'docx', 'txt'],
                key="file_uploader_empty"
            )
            uploaded_count = save_uploaded_files(uploaded_files, inbox_dir)
            if uploaded_count:
                st.success(f"Uploaded {uploaded_count} files to inbox!")
                st.rerun()

            st.caption(f"Inbox: `{inbox_dir}`")
        return

    # Inject CSS for tag chips and gallery
    st.markdown(TAG_CHIPS_CSS, unsafe_allow_html=True)

    # Breadcrumb navigation for browse mode
    if st.session_state.browse_mode:
        current_folder = st.session_state.get("browse_folder_input", output_dir)
        render_breadcrumb(Path(current_folder), Path(output_dir))

    # Get current file and analysis for toolbar
    current_file = st.session_state.current_file
    current_idx = st.session_state.current_file_idx

    # Ensure current_idx is valid
    if current_idx >= len(files):
        current_idx = 0
        st.session_state.current_file_idx = 0

    # Load analysis for current file (for toolbar pre-fill)
    current_analysis = None
    if current_file and current_file.exists():
        current_analysis = load_analysis(str(current_file))
    elif st.session_state.selection_mode and st.session_state.last_selected_file:
        # In selection mode, use last selected file for preview
        if st.session_state.last_selected_file.exists():
            current_analysis = load_analysis(str(st.session_state.last_selected_file))

    # ========== ACTIONS TOOLBAR (full width) ==========
    action, selected_area, selected_category = render_actions_toolbar(
        files=files,
        current_file=current_file if not st.session_state.selection_mode else st.session_state.last_selected_file,
        analysis=current_analysis,
        selection_mode=st.session_state.selection_mode,
        selected_files=st.session_state.selected_files,
        output_dir=output_dir,
        inbox_dir=inbox_dir
    )

    # Handle toolbar actions
    if action == "move":
        if st.session_state.selection_mode:
            # Bulk move
            moved = 0
            for file_str in list(st.session_state.selected_files):
                file_path = Path(file_str)
                if file_path.exists():
                    analysis = load_analysis(str(file_path))
                    extracted_text = analysis.get("extracted_text", "") if analysis else ""

                    if not extracted_text:
                        result = extract_text_with_docling(str(file_path))
                        if not result["success"] or not result["text"].strip():
                            result = extract_text_fallback(str(file_path))
                        if result["success"]:
                            extracted_text = result["text"]

                    final_analysis = {
                        "jd_area": selected_area,
                        "jd_category": selected_category,
                        "issuer": analysis.get("issuer") if analysis else None,
                        "document_type": analysis.get("document_type") if analysis else None,
                        "date_mentioned": analysis.get("date_mentioned") if analysis else None,
                        "subject_person": None,
                        "tags": analysis.get("tags", []) if analysis else [],
                        "confidence": "bulk",
                        "summary": analysis.get("summary", "") if analysis else "",
                        "entities": analysis.get("entities", []) if analysis else [],
                    }

                    try:
                        file_hash = get_file_hash(str(file_path))
                        original_name = file_path.name
                        dest_path = organize_file(str(file_path), output_dir, final_analysis, extracted_text)
                        delete_analysis_file(file_path)
                        processed = load_processed_files(output_dir)
                        mark_file_processed(file_hash, original_name, dest_path, processed)
                        save_processed_files(output_dir, processed)
                        moved += 1
                    except Exception as e:
                        st.error(f"Failed to move {file_path.name}: {e}")

            st.session_state.selected_files = set()
            st.session_state.processed_count += moved
            st.success(f"Moved {moved} files to {selected_area}/{selected_category}")
            st.rerun()
        else:
            # Single file move
            if current_file and current_file.exists():
                extracted_text = current_analysis.get("extracted_text", "") if current_analysis else ""

                if not extracted_text:
                    result = extract_text_with_docling(str(current_file))
                    if not result["success"] or not result["text"].strip():
                        result = extract_text_fallback(str(current_file))
                    if result["success"]:
                        extracted_text = result["text"]

                final_analysis = {
                    "jd_area": selected_area,
                    "jd_category": selected_category,
                    "issuer": current_analysis.get("issuer") if current_analysis else None,
                    "document_type": current_analysis.get("document_type") if current_analysis else None,
                    "date_mentioned": current_analysis.get("date_mentioned") if current_analysis else None,
                    "subject_person": None,
                    "tags": current_analysis.get("tags", []) if current_analysis else [],
                    "confidence": "manual",
                    "summary": current_analysis.get("summary", "") if current_analysis else "",
                    "entities": current_analysis.get("entities", []) if current_analysis else [],
                }

                try:
                    file_hash = get_file_hash(str(current_file))
                    original_name = current_file.name
                    dest_path = organize_file(str(current_file), output_dir, final_analysis, extracted_text)
                    delete_analysis_file(current_file)
                    processed = load_processed_files(output_dir)
                    mark_file_processed(file_hash, original_name, dest_path, processed)
                    save_processed_files(output_dir, processed)
                    st.session_state.processed_count += 1
                    st.session_state.current_file = None
                    st.success(f"Moved to {selected_area}/{selected_category}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to move: {e}")

    elif action == "reanalyze":
        if st.session_state.selection_mode:
            # Bulk reanalyze
            files_to_reanalyze = [f for f in st.session_state.selected_files if Path(f).exists()]
            total = len(files_to_reanalyze)
            if total > 0:
                progress_container = st.empty()
                processed_count = 0
                skipped_count = 0
                error_count = 0

                for idx, file_str in enumerate(files_to_reanalyze):
                    file_path = Path(file_str)
                    with progress_container.container():
                        st.info(f"Processing {idx + 1}/{total}: {file_path.name}")
                    try:
                        if reanalyze_file(file_path, skip_if_has_text=False):
                            processed_count += 1
                        else:
                            skipped_count += 1
                    except Exception as e:
                        error_count += 1

                progress_container.empty()
                msg_parts = [f"Processed {processed_count} files"]
                if skipped_count > 0:
                    msg_parts.append(f"skipped {skipped_count}")
                if error_count > 0:
                    msg_parts.append(f"{error_count} errors")
                st.success(", ".join(msg_parts))
                st.rerun()
        else:
            # Single file reanalyze
            if current_file and current_file.exists():
                with hand_spinner("Re-analyzing..."):
                    reanalyze_file(current_file, skip_if_has_text=False)
                st.rerun()

    elif action == "delete":
        if st.session_state.selection_mode:
            if st.session_state.get('confirm_bulk_delete'):
                deleted = 0
                for file_str in list(st.session_state.selected_files):
                    file_path = Path(file_str)
                    if file_path.exists():
                        delete_analysis_file(file_path)
                        file_path.unlink()
                        deleted += 1
                st.session_state.selected_files = set()
                st.session_state.confirm_bulk_delete = False
                st.success(f"Deleted {deleted} files")
                st.rerun()
            else:
                st.session_state.confirm_bulk_delete = True
                st.warning("Click Delete again to confirm")
        else:
            if current_file and current_file.exists():
                if st.session_state.get('confirm_display_delete'):
                    delete_analysis_file(current_file)
                    current_file.unlink()
                    st.session_state.current_file = None
                    st.session_state.confirm_display_delete = False
                    st.rerun()
                else:
                    st.session_state.confirm_display_delete = True
                    st.warning("Click Delete again to confirm")

    elif action == "reveal":
        if st.session_state.selection_mode:
            for file_str in st.session_state.selected_files:
                file_path = Path(file_str)
                if file_path.exists():
                    reveal_in_file_manager(file_path)
                    break
        else:
            if current_file and current_file.exists():
                reveal_in_file_manager(current_file)

    # ========== GALLERY STRIP (horizontal scrolling thumbnails) ==========
    clicked_idx, mode_changed = render_gallery_strip(
        files=files,
        current_idx=current_idx,
        selection_mode=st.session_state.selection_mode,
        selected_files=st.session_state.selected_files
    )

    # Handle gallery interactions
    if mode_changed is not None:
        if mode_changed:
            # Entering selection mode
            st.session_state.selection_mode = True
            st.session_state.current_file = None
            st.session_state.last_selected_file = None
        else:
            # Exiting selection mode
            st.session_state.selection_mode = False
            st.session_state.selected_files = set()
            st.session_state.checkbox_key_version += 1
            st.session_state.last_selected_file = None
        st.rerun()

    if clicked_idx is not None:
        st.session_state.current_file_idx = clicked_idx
        st.session_state.current_file = files[clicked_idx][0]
        st.rerun()

    # ========== PREVIEW SECTION (full width) ==========
    st.divider()

    # Determine which file to preview
    if st.session_state.selection_mode:
        preview_file = st.session_state.last_selected_file
    else:
        preview_file = st.session_state.current_file

    # Get analysis and text for preview
    preview_analysis = None
    preview_text = ""
    if preview_file and preview_file.exists():
        preview_analysis = load_analysis(str(preview_file))
        preview_text = preview_analysis.get("extracted_text", "") if preview_analysis else ""

    # Show file name if we have a file
    if preview_file and preview_file.exists():
        icon_subheader("file-scan", preview_file.name)

    render_preview(preview_file, preview_text)

    # ========== CLASSIFICATION SECTION (below preview) ==========
    if preview_file and preview_file.exists():
        st.divider()
        icon_subheader("tag", "Classification")
        render_classification(preview_analysis, preview_file)

        # Analyze button if no analysis
        if not preview_analysis:
            if st.button("Analyze Now", type="primary"):
                with hand_spinner("Analyzing..."):
                    preprocess_file(str(preview_file))
                st.rerun()


def render_settings_page():
    """Render the Settings page for configuring the application."""
    icon_title("settings", "Settings")

    settings = get_settings()

    # Sidebar navigation for Settings page
    with st.sidebar:
        st.caption(f"Library: `{Path(settings.output_dir).name}`")
        st.divider()

        # Navigation section - Documents/Settings
        icon_subheader("navigation", "Navigation")
        page = st.radio(
            "Go to",
            ["Documents", "Settings"],
            index=1,  # Settings is selected
            key="settings_nav_radio",
            horizontal=True,
            label_visibility="collapsed"
        )
        if page != st.session_state.nav_page:
            st.session_state.nav_page = page
            st.rerun()

    # Check if this is first run
    if not settings.setup_complete:
        st.info("Welcome! Please configure your settings below to get started.")

    # Create tabs for different settings categories
    tab_dirs, tab_ai, tab_jd, tab_about = st.tabs(["Directories", "AI Provider", "JD System", "About"])

    with tab_dirs:
        icon_subheader("folder-tree", "Directory Configuration")

        st.markdown("""
        Configure where your documents are stored. The **Output Directory** is the root
        of your Johnny.Decimal folder structure. The **Inbox** is where you place new
        documents for processing.
        """)

        # Output directory
        current_output = settings.get("output_dir", "")
        new_output = st.text_input(
            "Output Directory (JD Root)",
            value=current_output,
            placeholder=str(Path.home() / "Documents" / "jd_documents"),
            help="Root folder for your organized documents"
        )

        # Inbox directory
        current_inbox = settings.get("inbox_dir", "")
        default_inbox = str(Path(new_output or current_output) / "00-09 System" / "01 Inbox") if (new_output or current_output) else ""

        use_default_inbox = st.checkbox(
            "Use default inbox location",
            value=not current_inbox,
            help=f"Default: {{output_dir}}/00-09 System/01 Inbox"
        )

        if use_default_inbox:
            st.text_input(
                "Inbox Directory",
                value=default_inbox,
                disabled=True,
                help="Derived from output directory"
            )
            new_inbox = ""
        else:
            new_inbox = st.text_input(
                "Inbox Directory",
                value=current_inbox,
                placeholder=default_inbox,
                help="Where to place documents for processing"
            )

        # Validate and show status
        col1, col2 = st.columns(2)
        with col1:
            output_path = Path(new_output) if new_output else None
            if output_path:
                if output_path.exists():
                    st.success(f"Output directory exists")
                else:
                    st.warning("Directory will be created")

        with col2:
            inbox_path = Path(new_inbox) if new_inbox else Path(default_inbox) if default_inbox else None
            if inbox_path:
                if inbox_path.exists():
                    st.success(f"Inbox directory exists")
                else:
                    st.warning("Directory will be created")

        # Save button for directories
        if st.button("Save Directory Settings", type="primary", key="save_dirs"):
            if new_output:
                settings.set("output_dir", new_output)
            settings.set("inbox_dir", new_inbox)

            # Create directories if they don't exist
            success, error = settings.create_directories()
            if success:
                st.success("Settings saved and directories created!")
            else:
                st.error(f"Error creating directories: {error}")

    with tab_ai:
        icon_subheader("brain", "AI Provider Configuration")

        st.markdown("""
        Choose how documents are analyzed and categorized. You can use cloud AI services
        (requires API key), local AI (Ollama), or simple keyword matching (no AI).
        """)

        # Provider selection
        provider_options = {
            "auto": "Auto-detect (recommended)",
            "anthropic": "Anthropic Claude (API key required)",
            "openai": "OpenAI GPT (API key required)",
            "ollama": "Ollama (local, free)",
            "claude-code": "Claude Code CLI (requires Claude Max subscription)",
            "keywords": "Keywords only (no AI, always works)",
        }

        current_provider = settings.get("ai_provider", "auto")
        selected_provider = st.selectbox(
            "AI Provider",
            options=list(provider_options.keys()),
            format_func=lambda x: provider_options[x],
            index=list(provider_options.keys()).index(current_provider) if current_provider in provider_options else 0,
        )

        # Show relevant settings based on provider
        st.divider()

        if selected_provider in ["auto", "anthropic"]:
            st.markdown("**Anthropic Claude Settings**")
            anthropic_key = st.text_input(
                "Anthropic API Key",
                value=settings.get("anthropic_api_key", ""),
                type="password",
                help="Get your key at https://console.anthropic.com/"
            )

            anthropic_models = ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]
            current_model = settings.get("anthropic_model", "claude-sonnet-4-20250514")
            anthropic_model = st.selectbox(
                "Model",
                anthropic_models,
                index=anthropic_models.index(current_model) if current_model in anthropic_models else 0,
                key="anthropic_model_select"
            )

        if selected_provider in ["auto", "openai"]:
            st.markdown("**OpenAI Settings**")
            openai_key = st.text_input(
                "OpenAI API Key",
                value=settings.get("openai_api_key", ""),
                type="password",
                help="Get your key at https://platform.openai.com/api-keys"
            )

            openai_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
            current_model = settings.get("openai_model", "gpt-4o")
            openai_model = st.selectbox(
                "Model",
                openai_models,
                index=openai_models.index(current_model) if current_model in openai_models else 0,
                key="openai_model_select"
            )

        if selected_provider in ["auto", "ollama"]:
            st.markdown("**Ollama Settings** (Local AI)")
            ollama_url = st.text_input(
                "Ollama URL",
                value=settings.get("ollama_url", "http://localhost:11434"),
                help="Usually http://localhost:11434"
            )

            ollama_model = st.text_input(
                "Model",
                value=settings.get("ollama_model", "llama3.2"),
                help="e.g., llama3.2, mistral, mixtral"
            )

            # Test Ollama connection
            if st.button("Test Ollama Connection", key="test_ollama"):
                try:
                    import requests
                    response = requests.get(f"{ollama_url}/api/tags", timeout=5)
                    if response.status_code == 200:
                        models = [m["name"] for m in response.json().get("models", [])]
                        if models:
                            st.success(f"Connected! Available models: {', '.join(models[:5])}")
                        else:
                            st.warning("Connected but no models found. Run `ollama pull llama3.2`")
                    else:
                        st.error(f"Connection failed: {response.status_code}")
                except Exception as e:
                    st.error(f"Could not connect to Ollama: {e}")

        if selected_provider == "claude-code":
            st.markdown("**Claude Code CLI**")
            st.info("This uses the `claude` CLI tool which works with Claude Max subscription.")

            # Check if claude CLI is available
            if shutil.which("claude"):
                st.success("Claude CLI is installed and available")
            else:
                st.error("Claude CLI not found. Install with: `npm install -g @anthropic-ai/claude-code`")

        if selected_provider == "keywords":
            st.info("Keyword matching uses simple pattern matching to categorize documents. No AI or API keys required.")

        # Show effective provider
        st.divider()
        effective = settings.get_effective_provider()
        st.caption(f"Currently active provider: **{effective}**")

        # Save button for AI settings
        if st.button("Save AI Settings", type="primary", key="save_ai"):
            updates = {"ai_provider": selected_provider}

            if selected_provider in ["auto", "anthropic"]:
                updates["anthropic_api_key"] = anthropic_key
                updates["anthropic_model"] = anthropic_model
            if selected_provider in ["auto", "openai"]:
                updates["openai_api_key"] = openai_key
                updates["openai_model"] = openai_model
            if selected_provider in ["auto", "ollama"]:
                updates["ollama_url"] = ollama_url
                updates["ollama_model"] = ollama_model

            settings.update(updates)
            st.success("AI settings saved!")

    with tab_jd:
        render_jd_system_tab(settings)

    with tab_about:
        icon_subheader("info", "About Document Organizer")

        st.markdown("""
        **Document Organizer** automatically organizes your scanned documents using
        AI-powered categorization with the [Johnny.Decimal](https://johnnydecimal.com/) system.

        ### How it works

        1. **Drop documents** into your Inbox folder
        2. **AI analyzes** each document to determine its type, issuer, and category
        3. **Review suggestions** in this UI and adjust if needed
        4. **File documents** to their proper location in your JD structure

        ### Johnny.Decimal Structure

        Documents are organized into Areas and Categories:

        - **10-19 Finance** - Banking, Taxes, Insurance, Receipts
        - **20-29 Medical** - Records, Insurance, Prescriptions
        - **30-39 Legal** - Contracts, Property, Identity
        - **40-49 Work** - Employment, Projects, Certifications
        - **50-59 Personal** - Education, Travel, Memberships

        ### Links

        - [Johnny.Decimal System](https://johnnydecimal.com/)
        - [Project Documentation](https://github.com/yourusername/document-organizer)
        """)

        st.divider()

        # Show config location
        st.caption(f"Settings stored in: `{get_config_dir()}`")

        # Advanced settings
        with st.expander("Advanced"):
            st.markdown("**Maintenance**")

            # Show hash index status
            output_dir = settings.get("output_dir", "")
            if output_dir:
                hash_index = load_hash_index(output_dir)
                st.caption(f"Hash index contains {len(hash_index)} files")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Rebuild Hash Index", type="secondary", help="Scan all files and rebuild duplicate detection index"):
                    if output_dir:
                        with st.spinner("Scanning files and building hash index..."):
                            index = build_hash_index(output_dir, force_rebuild=True)
                        st.success(f"Hash index rebuilt: {len(index)} files indexed")
                        st.rerun()
                    else:
                        st.error("Please configure output directory first")

            with col2:
                if st.button("Reset All Settings", type="secondary"):
                    if st.session_state.get("confirm_reset"):
                        settings.reset()
                        st.success("Settings reset to defaults")
                        st.session_state.confirm_reset = False
                        st.rerun()
                    else:
                        st.session_state.confirm_reset = True
                        st.warning("Click again to confirm reset")

    # Mark setup as complete if user has configured directories
    if not settings.setup_complete and settings.get("output_dir"):
        settings.set("setup_complete", True)


def render_app():
    """Main app rendering - choose between setup wizard or main app."""
    settings = get_settings()

    # Check if first run - show setup wizard
    if not settings.setup_complete:
        render_setup_wizard()
        return

    # Initialize page in session state if not set
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "Documents"

    # Route to appropriate page
    if st.session_state.nav_page == "Documents":
        main()
    else:
        render_settings_page()


def render_setup_wizard():
    """First-run setup wizard."""
    icon_title("folder-check", "Welcome to Document Organizer")

    st.markdown("""
    Let's get you set up! This wizard will help you configure the essential settings.
    """)

    settings = get_settings()

    # Step 1: Directories
    icon_subheader("folder", "Step 1: Choose your document location")

    st.markdown("""
    Where would you like to store your organized documents?
    This will be the root of your Johnny.Decimal folder structure.
    """)

    default_output = str(Path.home() / "Documents" / "jd_documents")
    output_dir = st.text_input(
        "Document Library Location",
        value=settings.get("output_dir") or default_output,
        help="Your organized documents will be stored here"
    )

    # Step 2: AI Provider
    icon_subheader("brain", "Step 2: Choose AI provider (optional)")

    st.markdown("""
    AI helps categorize your documents automatically. Choose one:
    """)

    ai_choice = st.radio(
        "AI Provider",
        [
            ("ollama", "Ollama (free, runs locally) - Recommended for privacy"),
            ("anthropic", "Anthropic Claude (requires API key)"),
            ("keywords", "No AI (keyword matching only)"),
        ],
        format_func=lambda x: x[1],
        index=0,
    )
    selected_ai = ai_choice[0]

    if selected_ai == "anthropic":
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            help="Get your key at https://console.anthropic.com/"
        )
    elif selected_ai == "ollama":
        st.info("Make sure Ollama is installed and running. Visit https://ollama.ai to install.")

    # Complete setup
    st.divider()

    if st.button("Complete Setup", type="primary"):
        # Save settings
        updates = {
            "output_dir": output_dir,
            "inbox_dir": "",  # Use default
            "ai_provider": selected_ai,
            "setup_complete": True,
        }

        if selected_ai == "anthropic" and api_key:
            updates["anthropic_api_key"] = api_key

        settings.update(updates)

        # Create directories
        success, error = settings.create_directories()
        if success:
            st.success("Setup complete! Redirecting...")
            st.rerun()
        else:
            st.error(f"Error creating directories: {error}")


if __name__ == "__main__":
    render_app()
