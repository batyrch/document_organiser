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
from pathlib import Path
from datetime import datetime
import base64

# Import from main module
from document_organizer import (
    JD_AREAS,
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
    DEFAULT_JD_INBOX,
    DEFAULT_JD_OUTPUT,
)

# Page config
st.set_page_config(
    page_title="Document Organizer",
    page_icon="📁",
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

from contextlib import contextmanager

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


def get_inbox_files(inbox_dir: str) -> list[tuple[Path, bool, dict | None]]:
    """Get list of files in inbox with their analysis status and data.

    Recursively scans subfolders to find all documents.
    Returns list of (file_path, has_analysis, analysis_data) tuples.
    """
    supported = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.docx', '.pptx', '.xlsx', '.txt', '.html'}
    inbox = Path(inbox_dir)
    if not inbox.exists():
        return []

    files = []
    # Use rglob to recursively find all files in subfolders
    for f in sorted(inbox.rglob('*')):
        if f.is_file() and f.suffix.lower() in supported:
            analysis = load_analysis(str(f))
            files.append((f, analysis is not None, analysis))
    return files


def get_folder_files(folder_path: str, recursive: bool = True) -> list[tuple[Path, bool, dict | None]]:
    """Get list of files in any folder with their metadata status.

    Loads metadata from .meta.json sidecar files (for organized files).
    Returns list of (file_path, has_metadata, metadata) tuples.
    """
    supported = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.docx', '.pptx', '.xlsx', '.txt', '.html'}
    folder = Path(folder_path)
    if not folder.exists():
        return []

    files = []
    file_iter = folder.rglob("*") if recursive else folder.iterdir()

    for f in sorted(file_iter):
        if f.is_file() and f.suffix.lower() in supported:
            # Try .meta.json first (organized files)
            meta_path = f.with_suffix(f.suffix + ".meta.json")
            metadata = None
            if meta_path.exists():
                try:
                    with open(meta_path, 'r') as mf:
                        metadata = json.load(mf)
                except (json.JSONDecodeError, IOError):
                    pass

            # Fall back to .analysis.json (inbox files)
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


def get_all_organized_files(output_dir: str) -> list[tuple[Path, dict | None]]:
    """Get all organized files with their metadata for batch reanalysis."""
    output = Path(output_dir)
    if not output.exists():
        return []

    files = []
    supported = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.docx', '.pptx', '.xlsx', '.txt', '.html'}

    for f in output.rglob("*"):
        if f.is_file() and f.suffix.lower() in supported:
            # Load metadata if exists
            meta_path = f.with_suffix(f.suffix + ".meta.json")
            meta = None
            if meta_path.exists():
                try:
                    with open(meta_path, 'r') as mf:
                        meta = json.load(mf)
                except:
                    pass
            files.append((f, meta))

    return files


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
    st.image(str(file_path), use_container_width=True)


def get_areas_and_categories():
    """Get list of areas and their categories for dropdowns."""
    areas = []
    area_categories = {}
    for area, categories in JD_AREAS.items():
        if area == "00-09 System":
            # Only include Uncategorized from System area
            areas.append(area)
            area_categories[area] = ["09 Uncategorized"]
        elif area != "90-99 Archive":
            areas.append(area)
            area_categories[area] = list(categories.keys())
    return areas, area_categories


def delete_analysis_file(file_path: Path):
    """Delete the analysis JSON file for a document."""
    analysis_path = get_analysis_path(str(file_path))
    if analysis_path.exists():
        analysis_path.unlink()


def reanalyze_file(file_path: Path):
    """Delete existing analysis and reanalyze."""
    # Clean up orphaned analysis files in the same folder first
    cleanup_orphaned_analysis_files(file_path.parent)
    delete_analysis_file(file_path)
    preprocess_file(str(file_path))


def cleanup_orphaned_analysis_files(folder: Path) -> int:
    """Remove orphaned .analysis.json files in a folder, keeping only the latest one.

    An orphaned analysis file is one where no matching document exists.
    If multiple orphans exist, keep the most recent one (by modification time).

    Returns the number of deleted files.
    """
    if not folder.exists():
        return 0

    # Find all analysis files in the folder
    analysis_files = list(folder.glob("*.analysis.json"))
    if not analysis_files:
        return 0

    # Separate into matched and orphaned
    orphaned = []
    for analysis_path in analysis_files:
        # Get the original document name by removing .analysis.json suffix
        doc_name = analysis_path.name.replace(".analysis.json", "")
        doc_path = folder / doc_name
        if not doc_path.exists():
            orphaned.append(analysis_path)

    if not orphaned:
        return 0

    # Sort orphaned by modification time (newest first) and keep the latest
    orphaned.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # Delete all orphans (including the newest one)
    deleted = 0
    for old_analysis in orphaned:
        old_analysis.unlink()
        deleted += 1

    return deleted


def main():
    st.title("📁 Document Organizer")

    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        output_dir = st.text_input("Output Directory", value=DEFAULT_JD_OUTPUT)

        st.divider()

        # Source mode toggle
        st.subheader("📂 File Source")
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

            # Subfolder dropdown navigation
            if current_path.exists() and current_path.is_dir():
                subfolders = sorted([d.name for d in current_path.iterdir() if d.is_dir()])
                if subfolders:
                    options = ["(current folder)"] + subfolders

                    def navigate_subfolder():
                        selected = st.session_state.subfolder_select
                        if selected != "(current folder)":
                            current = st.session_state.browse_folder_input or output_dir
                            st.session_state.browse_folder_input = str(Path(current) / selected)

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
            # Inbox mode
            inbox_dir = st.text_input("Inbox Directory", value=DEFAULT_JD_INBOX)
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
            if st.button("🤖 Analyze All New Files", use_container_width=True):
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

        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # Search section
    st.subheader("🔍 Search")
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
            st.info(f"🔍 No files match '{search_query}' in {search_field}")
        else:
            st.info("📭 No files in inbox. Drop documents into the inbox folder to organize them.")
            st.code(inbox_dir)
        return

    # Main layout
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader(f"📥 Inbox ({len(files)} files)")

        # Bulk selection controls
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            if st.button("Select All", use_container_width=True):
                st.session_state.selected_files = {str(f) for f, _, _ in files}
                st.session_state.checkbox_key_version += 1
                st.rerun()
        with col_sel2:
            if st.button("Clear Selection", use_container_width=True):
                st.session_state.selected_files = set()
                st.session_state.checkbox_key_version += 1
                st.rerun()

        # Show selected count
        if st.session_state.selected_files:
            st.caption(f"Selected: {len(st.session_state.selected_files)} files")

        # File list with checkboxes
        for i, (file, analyzed, analysis) in enumerate(files):
            col_cb, col_btn = st.columns([0.15, 0.85])

            with col_cb:
                is_selected = str(file) in st.session_state.selected_files
                cb_key = f"sel_{i}_v{st.session_state.checkbox_key_version}"
                if st.checkbox("Select file", value=is_selected, key=cb_key, label_visibility="collapsed"):
                    st.session_state.selected_files.add(str(file))
                else:
                    st.session_state.selected_files.discard(str(file))

            with col_btn:
                status = "✅" if analyzed else "⏳"
                # Show issuer/type preview if available
                preview = ""
                if analysis:
                    issuer = analysis.get("issuer", "")
                    doc_type = analysis.get("document_type", "")
                    if issuer or doc_type:
                        preview = f" ({issuer or ''} - {doc_type or ''})"[:30]

                btn_label = f"{status} {file.name[:25]}{'...' if len(file.name) > 25 else ''}{preview}"
                if st.button(btn_label, key=f"file_{i}", use_container_width=True):
                    st.session_state.current_file = file
                    st.session_state.current_file_idx = i
                    st.rerun()

    with col2:
        # Bulk actions for selected files
        if st.session_state.selected_files:
            st.subheader(f"📦 Bulk Actions ({len(st.session_state.selected_files)} selected)")

            areas, area_categories = get_areas_and_categories()

            col_bulk1, col_bulk2 = st.columns(2)
            with col_bulk1:
                bulk_area = st.selectbox("Move to Area", areas, key="bulk_area")
            with col_bulk2:
                bulk_categories = area_categories.get(bulk_area, [])
                bulk_category = st.selectbox("Category", bulk_categories, key="bulk_cat")

            col_act1, col_act2, col_act3, col_act4 = st.columns(4)

            with col_act1:
                if st.button("📁 Move Selected", type="primary", use_container_width=True):
                    moved = 0
                    for file_str in list(st.session_state.selected_files):
                        file_path = Path(file_str)
                        if file_path.exists():
                            analysis = load_analysis(str(file_path))
                            extracted_text = analysis.get("extracted_text", "") if analysis else ""

                            final_analysis = {
                                "jd_area": bulk_area,
                                "jd_category": bulk_category,
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
                    st.success(f"Moved {moved} files to {bulk_area}/{bulk_category}")
                    st.rerun()

            with col_act2:
                if st.button("🔄 Reanalyze Selected", use_container_width=True):
                    files_to_reanalyze = [f for f in st.session_state.selected_files if Path(f).exists()]
                    total = len(files_to_reanalyze)

                    if total > 0:
                        progress_container = st.empty()

                        for idx, file_str in enumerate(files_to_reanalyze):
                            file_path = Path(file_str)
                            processed = idx
                            remaining = total - idx

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

                            reanalyze_file(file_path)

                        progress_container.empty()

                    st.success(f"Reanalyzed {total} files")
                    st.rerun()

            with col_act3:
                if st.button("🗑️ Delete Selected", use_container_width=True):
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

            with col_act4:
                if st.button("📂 Reveal in Finder", key="bulk_reveal", use_container_width=True):
                    import subprocess
                    for file_str in st.session_state.selected_files:
                        file_path = Path(file_str)
                        if file_path.exists():
                            subprocess.run(["open", "-R", str(file_path)])
                            break  # Only reveal first selected file

            st.divider()

        # Single file view
        if st.session_state.current_file is None:
            st.info("👈 Select a file from the inbox to preview and classify")
            st.markdown("""
            **Workflow:**
            1. Files with ✅ have been analyzed (AI suggestion ready)
            2. Files with ⏳ need analysis - click "Analyze All New Files"
            3. Select a file, review the suggestion, adjust if needed
            4. Click "Process & File" to organize

            **Bulk Actions:**
            - Use checkboxes to select multiple files
            - Choose area/category and click "Move Selected"
            """)
            return

        file_path = st.session_state.current_file

        if not file_path.exists():
            st.error("File no longer exists. It may have been processed.")
            st.session_state.current_file = None
            st.rerun()
            return

        # Navigation buttons
        col_nav1, col_nav2, col_nav3 = st.columns([1, 3, 1])
        with col_nav1:
            if st.button("⬅️ Prev", use_container_width=True):
                if st.session_state.current_file_idx > 0:
                    st.session_state.current_file_idx -= 1
                    st.session_state.current_file = files[st.session_state.current_file_idx][0]
                    st.rerun()
        with col_nav2:
            st.markdown(f"**{st.session_state.current_file_idx + 1} / {len(files)}**",
                       unsafe_allow_html=True)
        with col_nav3:
            if st.button("Next ➡️", use_container_width=True):
                if st.session_state.current_file_idx < len(files) - 1:
                    st.session_state.current_file_idx += 1
                    st.session_state.current_file = files[st.session_state.current_file_idx][0]
                    st.rerun()

        st.subheader(f"📄 {file_path.name}")

        # Load existing analysis if available
        analysis = load_analysis(str(file_path))
        extracted_text = analysis.get("extracted_text", "") if analysis else ""

        # Preview tabs
        tab1, tab2 = st.tabs(["Preview", "Extracted Text"])

        with tab1:
            suffix = file_path.suffix.lower()
            if suffix == '.pdf':
                display_pdf(file_path)
            elif suffix in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                display_image(file_path)
            else:
                st.info(f"Preview not available for {suffix} files. Check 'Extracted Text' tab.")

        with tab2:
            if not extracted_text:
                st.warning("No extracted text available. Click 'Analyze This File' to extract.")
                if st.button("📖 Analyze This File"):
                    with hand_spinner("Extracting and analyzing..."):
                        preprocess_file(str(file_path))
                    st.rerun()
            else:
                st.text_area("Extracted Text", extracted_text, height=400, disabled=True)

        st.divider()

        # Classification section
        st.subheader("🏷️ Classification")

        # Show analysis status
        if analysis:
            with st.expander("🤖 AI Analysis", expanded=True):
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.write(f"**Suggested Area:** {analysis.get('jd_area', 'Unknown')}")
                    st.write(f"**Suggested Category:** {analysis.get('jd_category', 'Unknown')}")
                    st.write(f"**Confidence:** {analysis.get('confidence', 'Unknown')}")
                with col_s2:
                    st.write(f"**Issuer:** {analysis.get('issuer', 'Unknown')}")
                    st.write(f"**Document Type:** {analysis.get('document_type', 'Unknown')}")
                    st.write(f"**Date:** {analysis.get('date_mentioned', 'Not found')}")
                st.write(f"**Summary:** {analysis.get('summary', 'No summary')}")
                if analysis.get('tags'):
                    st.write(f"**Tags:** {', '.join(analysis.get('tags', []))}")

                # Re-analyze button
                if st.button("🔄 Re-analyze with AI"):
                    with hand_spinner("Re-analyzing..."):
                        reanalyze_file(file_path)
                    st.rerun()
        else:
            st.warning("⏳ This file hasn't been analyzed yet.")
            if st.button("🤖 Analyze Now", type="primary"):
                with hand_spinner("Analyzing..."):
                    preprocess_file(str(file_path))
                st.rerun()
            return

        st.divider()

        # Manual classification form
        st.subheader("✏️ Final Classification")
        st.caption("Adjust the AI suggestions or keep them as-is")

        areas, area_categories = get_areas_and_categories()

        # Pre-fill from analysis
        default_area_idx = 0
        default_cat_idx = 0
        default_issuer = ""
        default_doc_type = ""
        default_date = ""
        default_tags = ""

        if analysis:
            ai_area = analysis.get('jd_area', '')
            if ai_area in areas:
                default_area_idx = areas.index(ai_area)
            ai_cat = analysis.get('jd_category', '')
            if ai_area in area_categories and ai_cat in area_categories[ai_area]:
                default_cat_idx = area_categories[ai_area].index(ai_cat)
            default_issuer = analysis.get('issuer', '') or ''
            default_doc_type = analysis.get('document_type', '') or ''
            default_date = analysis.get('date_mentioned', '') or ''
            default_tags = ', '.join(analysis.get('tags', []))

        # Form
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            selected_area = st.selectbox("Area", areas, index=default_area_idx)
            categories = area_categories.get(selected_area, [])

            # Adjust default category index if area changed
            if selected_area != areas[default_area_idx]:
                default_cat_idx = 0
            elif default_cat_idx >= len(categories):
                default_cat_idx = 0

            selected_category = st.selectbox("Category", categories, index=default_cat_idx)
            issuer = st.text_input("Issuer (Organization)", value=default_issuer)

        with col_f2:
            document_type = st.text_input("Document Type", value=default_doc_type)
            document_date = st.text_input("Document Date (YYYY-MM-DD)", value=default_date)
            tags = st.text_input("Tags (comma-separated)", value=default_tags)

        subject_person = st.text_input("Subject Person (only if document is about someone else)", value="")

        st.divider()

        # Action buttons
        col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns([1, 1, 1, 1, 1])

        with col_a1:
            if st.button("✅ Process & File", type="primary", use_container_width=True):
                # Build final analysis dict from form
                final_analysis = {
                    "jd_area": selected_area,
                    "jd_category": selected_category,
                    "issuer": issuer if issuer else None,
                    "document_type": document_type if document_type else None,
                    "date_mentioned": document_date if document_date else None,
                    "subject_person": subject_person if subject_person else None,
                    "tags": [t.strip() for t in tags.split(',') if t.strip()],
                    "confidence": "manual",
                    "summary": analysis.get('summary', '') if analysis else '',
                    "entities": analysis.get('entities', []) if analysis else [],
                }

                # Get file hash before moving
                file_hash = get_file_hash(str(file_path))
                original_name = file_path.name

                with hand_spinner("Filing document..."):
                    try:
                        dest_path = organize_file(
                            str(file_path),
                            output_dir,
                            final_analysis,
                            extracted_text
                        )

                        # Delete the analysis file (document has been moved)
                        delete_analysis_file(file_path)

                        # Mark as processed
                        processed = load_processed_files(output_dir)
                        mark_file_processed(file_hash, original_name, dest_path, processed)
                        save_processed_files(output_dir, processed)

                        st.session_state.processed_count += 1
                        st.success(f"✅ Filed to: {dest_path}")

                        # Move to next file
                        if st.session_state.current_file_idx < len(files) - 1:
                            st.session_state.current_file_idx += 1
                            # Refresh file list since one was removed
                            new_files = get_inbox_files(inbox_dir)
                            new_files = filter_files(new_files, search_query, search_field)
                            if new_files and st.session_state.current_file_idx < len(new_files):
                                st.session_state.current_file = new_files[st.session_state.current_file_idx][0]
                            else:
                                st.session_state.current_file = None
                        else:
                            st.session_state.current_file = None

                        st.rerun()

                    except Exception as e:
                        st.error(f"Error filing document: {e}")

        with col_a2:
            if st.button("⏭️ Skip", use_container_width=True):
                # Move to next file
                if st.session_state.current_file_idx < len(files) - 1:
                    st.session_state.current_file_idx += 1
                    st.session_state.current_file = files[st.session_state.current_file_idx][0]
                else:
                    st.session_state.current_file = None
                st.rerun()

        with col_a3:
            if st.button("⬅️ Previous", use_container_width=True):
                if st.session_state.current_file_idx > 0:
                    st.session_state.current_file_idx -= 1
                    st.session_state.current_file = files[st.session_state.current_file_idx][0]
                    st.rerun()

        with col_a4:
            if st.button("🗑️ Delete", use_container_width=True):
                if st.session_state.get('confirm_delete'):
                    # Delete both document and analysis
                    delete_analysis_file(file_path)
                    file_path.unlink()
                    st.session_state.current_file = None
                    st.session_state.confirm_delete = False
                    st.rerun()
                else:
                    st.session_state.confirm_delete = True
                    st.warning("Click Delete again to confirm")

        with col_a5:
            if st.button("📂 Reveal in Finder", key="single_reveal", use_container_width=True):
                import subprocess
                subprocess.run(["open", "-R", str(file_path)])


if __name__ == "__main__":
    main()
