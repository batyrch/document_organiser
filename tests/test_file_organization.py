"""
Tests for file organization and JD ID management.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from document_organizer import (
    slugify,
    extract_year,
    generate_folder_descriptor,
    generate_filename,
    get_jd_ids_path,
    load_jd_ids,
    save_jd_ids,
    get_or_create_jd_id,
)


class TestSlugify:
    """Tests for the slugify function."""

    def test_basic_slugify(self):
        """Test basic string slugification."""
        assert slugify("Hello World") == "Hello_World"

    def test_special_characters(self):
        """Test removal of special characters."""
        assert slugify("Hello! World?") == "Hello_World"
        assert slugify("Price: $100") == "Price_100"

    def test_multiple_spaces(self):
        """Test handling of multiple spaces."""
        assert slugify("Hello    World") == "Hello_World"

    def test_leading_trailing_spaces(self):
        """Test trimming of leading/trailing spaces."""
        assert slugify("  Hello World  ") == "Hello_World"

    def test_german_characters(self):
        """Test handling of German umlauts."""
        # Depending on implementation, umlauts might be kept or converted
        result = slugify("Müller Straße")
        assert "_" in result or result  # Should at least not crash

    def test_empty_string(self):
        """Test handling of empty string."""
        result = slugify("")
        assert result == "" or result == "_"


class TestExtractYear:
    """Tests for year extraction from dates."""

    def test_iso_date(self):
        """Test extraction from ISO format date."""
        assert extract_year("2024-12-20") == "2024"

    def test_european_date(self):
        """Test extraction from European format date."""
        assert extract_year("20.12.2024") == "2024"

    def test_us_date(self):
        """Test extraction from US format date."""
        assert extract_year("12/20/2024") == "2024"

    def test_year_only(self):
        """Test extraction when only year is provided."""
        assert extract_year("2024") == "2024"

    def test_none_input(self):
        """Test handling of None input."""
        result = extract_year(None)
        # Should return current year or empty string
        assert result is None or len(result) == 4

    def test_invalid_date(self):
        """Test handling of invalid date string."""
        result = extract_year("not a date")
        assert result is None or result == ""


class TestGenerateFolderDescriptor:
    """Tests for folder descriptor generation."""

    def test_basic_descriptor(self):
        """Test basic descriptor generation."""
        result = generate_folder_descriptor("Amazon", "Laptop Receipt")
        assert "Amazon" in result
        assert "Laptop" in result or "Receipt" in result

    def test_long_issuer(self):
        """Test truncation of long issuer names."""
        long_issuer = "A" * 100
        result = generate_folder_descriptor(long_issuer, "Receipt")
        # Should be reasonably truncated
        assert len(result) < 150

    def test_special_characters_removed(self):
        """Test that special characters are handled."""
        result = generate_folder_descriptor("Amazon.de", "Receipt #123")
        # Should not contain problematic filesystem characters
        assert "/" not in result
        assert "\\" not in result


class TestGenerateFilename:
    """Tests for filename generation."""

    def test_basic_filename(self):
        """Test basic filename generation."""
        result = generate_filename(
            jd_id="14.01",
            issuer="Amazon",
            document_type="Laptop Receipt",
            year="2024",
            extension=".pdf"
        )
        assert result.startswith("14.01")
        assert "Amazon" in result
        assert "2024" in result
        assert result.endswith(".pdf")

    def test_filename_without_year(self):
        """Test filename generation without year."""
        result = generate_filename(
            jd_id="14.01",
            issuer="Amazon",
            document_type="Receipt",
            year=None,
            extension=".pdf"
        )
        assert "14.01" in result
        assert result.endswith(".pdf")


class TestJDIdManagement:
    """Tests for JD ID tracking and assignment."""

    def test_get_jd_ids_path(self, output_dir: Path):
        """Test that JD IDs path is correct."""
        path = get_jd_ids_path(str(output_dir))
        assert path.name == "_jd_ids.json"
        assert path.parent == output_dir

    def test_load_jd_ids_empty(self, output_dir: Path):
        """Test loading when no IDs file exists."""
        ids = load_jd_ids(str(output_dir))
        assert ids == {}

    def test_save_and_load_jd_ids(self, output_dir: Path):
        """Test saving and loading JD IDs."""
        test_ids = {"14": 5, "21": 3}
        save_jd_ids(str(output_dir), test_ids)

        loaded = load_jd_ids(str(output_dir))
        assert loaded == test_ids

    def test_get_or_create_jd_id_new(self, output_dir: Path):
        """Test creating a new JD ID."""
        jd_id = get_or_create_jd_id(
            output_dir=str(output_dir),
            category_num="14",
            issuer="Amazon",
            year="2024"
        )
        assert jd_id.startswith("14.")
        assert len(jd_id.split(".")) == 2

    def test_get_or_create_jd_id_same_issuer_year(self, output_dir: Path):
        """Test that same issuer+year gets same ID."""
        jd_id_1 = get_or_create_jd_id(
            output_dir=str(output_dir),
            category_num="14",
            issuer="Amazon",
            year="2024"
        )
        jd_id_2 = get_or_create_jd_id(
            output_dir=str(output_dir),
            category_num="14",
            issuer="Amazon",
            year="2024"
        )
        assert jd_id_1 == jd_id_2

    def test_get_or_create_jd_id_different_issuer(self, output_dir: Path):
        """Test that different issuers get different IDs."""
        jd_id_amazon = get_or_create_jd_id(
            output_dir=str(output_dir),
            category_num="14",
            issuer="Amazon",
            year="2024"
        )
        jd_id_tk = get_or_create_jd_id(
            output_dir=str(output_dir),
            category_num="14",
            issuer="TK Insurance",
            year="2024"
        )
        assert jd_id_amazon != jd_id_tk

    def test_get_or_create_jd_id_different_year(self, output_dir: Path):
        """Test that different years get different IDs."""
        jd_id_2024 = get_or_create_jd_id(
            output_dir=str(output_dir),
            category_num="14",
            issuer="Amazon",
            year="2024"
        )
        jd_id_2023 = get_or_create_jd_id(
            output_dir=str(output_dir),
            category_num="14",
            issuer="Amazon",
            year="2023"
        )
        assert jd_id_2024 != jd_id_2023


class TestFileHashing:
    """Tests for file hash tracking."""

    def test_get_file_hash(self, sample_pdf_path: Path):
        """Test file hash generation."""
        from document_organizer import get_file_hash

        hash1 = get_file_hash(str(sample_pdf_path))
        hash2 = get_file_hash(str(sample_pdf_path))

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_different_files_different_hash(self, inbox_dir: Path):
        """Test that different files have different hashes."""
        from document_organizer import get_file_hash

        file1 = inbox_dir / "file1.txt"
        file2 = inbox_dir / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        hash1 = get_file_hash(str(file1))
        hash2 = get_file_hash(str(file2))

        assert hash1 != hash2
