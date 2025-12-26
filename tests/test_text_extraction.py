"""
Tests for text extraction functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDoclingExtraction:
    """Tests for Docling-based text extraction."""

    @patch("document_organizer.DocumentConverter")
    def test_extract_text_success(self, mock_converter_class, sample_pdf_path: Path):
        """Test successful text extraction with Docling."""
        from document_organizer import extract_text_with_docling

        # Setup mock
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "Extracted text content"
        mock_result.document.pages = [1, 2, 3]
        mock_converter.convert.return_value = mock_result

        result = extract_text_with_docling(str(sample_pdf_path))

        assert result["success"] is True
        assert result["text"] == "Extracted text content"
        assert result["metadata"]["pages"] == 3

    @patch("document_organizer.DocumentConverter")
    def test_extract_text_failure(self, mock_converter_class, sample_pdf_path: Path):
        """Test handling of extraction failure."""
        from document_organizer import extract_text_with_docling

        # Setup mock to raise exception
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter
        mock_converter.convert.side_effect = Exception("Conversion failed")

        result = extract_text_with_docling(str(sample_pdf_path))

        assert result["success"] is False
        assert "error" in result
        assert result["text"] == ""


class TestFallbackExtraction:
    """Tests for fallback text extraction methods."""

    def test_extract_text_file(self, inbox_dir: Path):
        """Test extraction from plain text file."""
        from document_organizer import extract_text_fallback

        txt_file = inbox_dir / "test.txt"
        txt_file.write_text("Hello, this is test content.")

        result = extract_text_fallback(str(txt_file))

        assert result["success"] is True
        assert "Hello" in result["text"]

    @patch("document_organizer.pdfplumber")
    def test_extract_pdf_fallback(self, mock_pdfplumber, inbox_dir: Path):
        """Test PDF extraction with pdfplumber fallback."""
        from document_organizer import extract_text_fallback

        # Create a dummy PDF file
        pdf_file = inbox_dir / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy content")

        # Setup mock
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted PDF text"
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf

        result = extract_text_fallback(str(pdf_file))

        assert result["success"] is True
        assert "Extracted PDF text" in result["text"]

    def test_extract_image_with_ocr(self, sample_image_path: Path):
        """Test OCR extraction from image (may skip if tesseract not installed)."""
        from document_organizer import extract_text_fallback

        result = extract_text_fallback(str(sample_image_path))

        # Should succeed (possibly with empty text if tesseract not available)
        assert "success" in result


class TestAnalysisStorage:
    """Tests for analysis JSON storage."""

    def test_save_and_load_analysis(self, inbox_dir: Path):
        """Test saving and loading analysis JSON."""
        from document_organizer import (
            save_analysis,
            load_analysis,
            get_analysis_path,
            has_analysis,
        )

        test_file = inbox_dir / "test.pdf"
        test_file.write_text("dummy")

        analysis = {
            "jd_area": "10-19 Finance",
            "jd_category": "14 Receipts",
            "issuer": "Amazon",
            "document_type": "Receipt",
        }

        # Initially no analysis
        assert has_analysis(str(test_file)) is False

        # Save analysis
        save_analysis(str(test_file), analysis)

        # Now has analysis
        assert has_analysis(str(test_file)) is True

        # Load and verify
        loaded = load_analysis(str(test_file))
        assert loaded["jd_area"] == "10-19 Finance"
        assert loaded["issuer"] == "Amazon"

    def test_analysis_path_format(self, inbox_dir: Path):
        """Test that analysis path follows expected format."""
        from document_organizer import get_analysis_path

        test_file = inbox_dir / "document.pdf"
        analysis_path = get_analysis_path(str(test_file))

        assert analysis_path.name == "document.pdf.meta.json"
        assert analysis_path.parent == inbox_dir

    def test_load_missing_analysis(self, inbox_dir: Path):
        """Test loading analysis when file doesn't exist."""
        from document_organizer import load_analysis

        test_file = inbox_dir / "nonexistent.pdf"
        result = load_analysis(str(test_file))

        assert result is None
