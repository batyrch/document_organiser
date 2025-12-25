"""
Lucide Icons for Document Organizer UI

This module provides SVG icon definitions from Lucide Icons (https://lucide.dev/).
Icons are MIT licensed and rendered as inline SVG for use with Streamlit.
"""

# Lucide icon SVG paths - each icon is a dict with 'paths' (list of path d attributes)
# and optionally 'circles', 'rects', 'lines', 'polylines' for complex shapes
LUCIDE_ICONS = {
    # File type icons
    "file-text": {
        "paths": [
            "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z",
            "M14 2v4a2 2 0 0 0 2 2h4",
            "M10 9H8",
            "M16 13H8",
            "M16 17H8",
        ],
    },
    "image": {
        "paths": [
            "M21 3H3a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2Z",
            "m21 15-5-5L5 21",
        ],
        "circles": [{"cx": 9, "cy": 9, "r": 2}],
    },
    "file-edit": {
        "paths": [
            "M12 22h6a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v10",
            "M14 2v4a2 2 0 0 0 2 2h4",
            "M10.4 12.6a2 2 0 1 1 3 3L8 21l-4 1 1-4Z",
        ],
    },
    "sheet": {
        "paths": [
            "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z",
            "M14 2v4a2 2 0 0 0 2 2h4",
            "M8 18v-2",
            "M12 18v-6",
            "M16 18v-4",
        ],
    },
    "presentation": {
        "paths": [
            "M2 3h20",
            "M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3",
            "m7 21 5-5 5 5",
        ],
    },
    "file": {
        "paths": [
            "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z",
            "M14 2v4a2 2 0 0 0 2 2h4",
        ],
    },
    "globe": {
        "circles": [{"cx": 12, "cy": 12, "r": 10}],
        "paths": [
            "M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20",
            "M2 12h20",
        ],
    },
    "folder": {
        "paths": [
            "M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z",
        ],
    },

    # Action button icons
    "brain": {
        "paths": [
            "M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z",
            "M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z",
            "M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4",
            "M17.599 6.5a3 3 0 0 0 .399-1.375",
            "M6.003 5.125A3 3 0 0 0 6.401 6.5",
            "M3.477 10.896a4 4 0 0 1 .585-.396",
            "M19.938 10.5a4 4 0 0 1 .585.396",
            "M6 18a4 4 0 0 1-1.967-.516",
            "M19.967 17.484A4 4 0 0 1 18 18",
        ],
    },
    "refresh-cw": {
        "paths": [
            "M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8",
            "M21 3v5h-5",
            "M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16",
            "M3 21v-5h5",
        ],
    },
    "rotate-ccw": {
        "paths": [
            "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8",
            "M3 3v5h5",
        ],
    },
    "folder-open": {
        "paths": [
            "m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2",
        ],
    },
    "folder-input": {
        "paths": [
            "M2 9V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-1",
            "M2 13h10",
            "m9 16 3-3-3-3",
        ],
    },
    "trash-2": {
        "paths": [
            "M3 6h18",
            "M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6",
            "M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2",
        ],
        "lines": [
            {"x1": 10, "y1": 11, "x2": 10, "y2": 17},
            {"x1": 14, "y1": 11, "x2": 14, "y2": 17},
        ],
    },
    "check-circle": {
        "paths": [
            "M22 11.08V12a10 10 0 1 1-5.93-9.14",
            "m9 11 3 3L22 4",
        ],
    },
    "skip-forward": {
        "paths": [
            "m5 4 10 8-10 8V4Z",
        ],
        "lines": [{"x1": 19, "y1": 5, "x2": 19, "y2": 19}],
    },
    "chevron-left": {
        "paths": ["m15 18-6-6 6-6"],
    },
    "chevron-right": {
        "paths": ["m9 18 6-6-6-6"],
    },
    "upload": {
        "paths": [
            "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4",
            "m17 8-5-5-5 5",
            "M12 3v12",
        ],
    },
    "scan-text": {
        "paths": [
            "M3 7V5a2 2 0 0 1 2-2h2",
            "M17 3h2a2 2 0 0 1 2 2v2",
            "M21 17v2a2 2 0 0 1-2 2h-2",
            "M7 21H5a2 2 0 0 1-2-2v-2",
            "M7 8h8",
            "M7 12h10",
            "M7 16h6",
        ],
    },

    # Section header icons
    "folder-check": {
        "paths": [
            "M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z",
            "m9 13 2 2 4-4",
        ],
    },
    "folder-tree": {
        "paths": [
            "M20 10a2 2 0 0 0-2-2h-4.586a2 2 0 0 1-1.414-.586l-.828-.828A2 2 0 0 0 9.758 6H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4Z",
            "M3 6v12",
        ],
    },
    "search": {
        "circles": [{"cx": 11, "cy": 11, "r": 8}],
        "paths": ["m21 21-4.3-4.3"],
    },
    "inbox": {
        "paths": [
            "M22 12h-6l-2 3H10l-2-3H2",
            "M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z",
        ],
    },
    "layers": {
        "paths": [
            "m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z",
            "m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65",
            "m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65",
        ],
    },
    "file-scan": {
        "paths": [
            "M20 10V7l-5-5H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h4",
            "M14 2v4a2 2 0 0 0 2 2h4",
            "M16 14a2 2 0 0 0-2 2",
            "M20 14a2 2 0 0 1 2 2",
            "M20 22a2 2 0 0 0 2-2",
            "M16 22a2 2 0 0 1-2-2",
        ],
    },
    "tag": {
        "paths": [
            "M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z",
        ],
        "circles": [{"cx": 7.5, "cy": 7.5, "r": 0.5, "fill": "currentColor"}],
    },
    "edit-3": {
        "paths": [
            "M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z",
        ],
    },

    # Status indicators
    "clock": {
        "circles": [{"cx": 12, "cy": 12, "r": 10}],
        "paths": ["M12 6v6l4 2"],
    },
    "list": {
        "paths": [
            "M3 12h.01",
            "M3 18h.01",
            "M3 6h.01",
            "M8 12h13",
            "M8 18h13",
            "M8 6h13",
        ],
    },
    "grid-3x3": {
        "rects": [
            {"x": 3, "y": 3, "width": 7, "height": 7},
            {"x": 14, "y": 3, "width": 7, "height": 7},
            {"x": 14, "y": 14, "width": 7, "height": 7},
            {"x": 3, "y": 14, "width": 7, "height": 7},
        ],
    },

    # Other icons
    "map-pin": {
        "paths": [
            "M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z",
        ],
        "circles": [{"cx": 12, "cy": 10, "r": 3}],
    },
    "arrow-left": {
        "paths": [
            "m12 19-7-7 7-7",
            "M19 12H5",
        ],
    },
    "arrow-right": {
        "paths": [
            "M5 12h14",
            "m12 5 7 7-7 7",
        ],
    },
    "settings": {
        "paths": [
            "M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z",
        ],
        "circles": [{"cx": 12, "cy": 12, "r": 3}],
    },
    "info": {
        "circles": [{"cx": 12, "cy": 12, "r": 10}],
        "paths": [
            "M12 16v-4",
            "M12 8h.01",
        ],
    },
    "alert-circle": {
        "circles": [{"cx": 12, "cy": 12, "r": 10}],
        "paths": [
            "M12 8v4",
            "M12 16h.01",
        ],
    },
    "x": {
        "paths": [
            "M18 6 6 18",
            "m6 6 12 12",
        ],
    },
    "check": {
        "paths": ["M20 6 9 17l-5-5"],
    },
    "plus": {
        "paths": [
            "M5 12h14",
            "M12 5v14",
        ],
    },
    "minus": {
        "paths": ["M5 12h14"],
    },
    "eye": {
        "paths": [
            "M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0",
        ],
        "circles": [{"cx": 12, "cy": 12, "r": 3}],
    },
    "eye-off": {
        "paths": [
            "M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49",
            "M14.084 14.158a3 3 0 0 1-4.242-4.242",
            "M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143",
            "m2 2 20 20",
        ],
    },
    "download": {
        "paths": [
            "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4",
            "m7 10 5 5 5-5",
            "M12 15V3",
        ],
    },
    "external-link": {
        "paths": [
            "M15 3h6v6",
            "M10 14 21 3",
            "M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6",
        ],
    },
}


def lucide_icon(
    name: str,
    size: int = 20,
    color: str = "currentColor",
    stroke_width: float = 2,
    class_name: str = "",
) -> str:
    """
    Render a Lucide icon as inline SVG HTML.

    Args:
        name: Icon name (e.g., 'file-text', 'folder', 'search')
        size: Icon size in pixels (default 20)
        color: Icon color (default 'currentColor' to inherit)
        stroke_width: Stroke width (default 2)
        class_name: Optional CSS class to add to the SVG

    Returns:
        HTML string containing the SVG icon
    """
    if name not in LUCIDE_ICONS:
        # Return a placeholder for unknown icons
        return f'<span style="display:inline-block;width:{size}px;height:{size}px;background:#ccc;border-radius:2px;"></span>'

    icon = LUCIDE_ICONS[name]
    elements = []

    # Add paths
    for path_d in icon.get("paths", []):
        elements.append(f'<path d="{path_d}"/>')

    # Add circles
    for circle in icon.get("circles", []):
        fill = circle.get("fill", "none")
        elements.append(
            f'<circle cx="{circle["cx"]}" cy="{circle["cy"]}" r="{circle["r"]}" fill="{fill}"/>'
        )

    # Add rectangles
    for rect in icon.get("rects", []):
        rx = rect.get("rx", 0)
        elements.append(
            f'<rect x="{rect["x"]}" y="{rect["y"]}" width="{rect["width"]}" height="{rect["height"]}" rx="{rx}"/>'
        )

    # Add lines
    for line in icon.get("lines", []):
        elements.append(
            f'<line x1="{line["x1"]}" y1="{line["y1"]}" x2="{line["x2"]}" y2="{line["y2"]}"/>'
        )

    # Add polylines
    for polyline in icon.get("polylines", []):
        elements.append(f'<polyline points="{polyline["points"]}"/>')

    class_attr = f' class="{class_name}"' if class_name else ""

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round"{class_attr} style="display:inline-block;vertical-align:middle;">{''.join(elements)}</svg>'''

    return svg


def icon_with_text(
    icon_name: str,
    text: str,
    size: int = 20,
    color: str = "currentColor",
    gap: int = 6,
) -> str:
    """
    Render an icon followed by text, properly aligned.

    Args:
        icon_name: Lucide icon name
        text: Text to display after the icon
        size: Icon size in pixels
        color: Icon color
        gap: Gap between icon and text in pixels

    Returns:
        HTML string with icon and text
    """
    icon_svg = lucide_icon(icon_name, size=size, color=color)
    return f'<span style="display:inline-flex;align-items:center;gap:{gap}px;">{icon_svg}<span>{text}</span></span>'


def status_icon(analyzed: bool, size: int = 16) -> str:
    """
    Render a status icon for file analysis state.

    Args:
        analyzed: Whether the file has been analyzed
        size: Icon size in pixels

    Returns:
        HTML string with colored status icon
    """
    if analyzed:
        return lucide_icon("check-circle", size=size, color="#27ae60")
    else:
        return lucide_icon("clock", size=size, color="#f39c12")


def file_type_icon(suffix: str, size: int = 20) -> str:
    """
    Get the appropriate icon for a file type.

    Args:
        suffix: File extension (e.g., '.pdf', '.png')
        size: Icon size in pixels

    Returns:
        HTML string with file type icon
    """
    icon_map = {
        ".pdf": "file-text",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".tiff": "image",
        ".bmp": "image",
        ".gif": "image",
        ".docx": "file-edit",
        ".doc": "file-edit",
        ".xlsx": "sheet",
        ".xls": "sheet",
        ".pptx": "presentation",
        ".ppt": "presentation",
        ".txt": "file",
        ".html": "globe",
        ".htm": "globe",
    }
    icon_name = icon_map.get(suffix.lower(), "folder")
    return lucide_icon(icon_name, size=size)
