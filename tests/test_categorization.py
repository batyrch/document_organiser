"""
Tests for document categorization functionality.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

# Import the module under test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from document_organizer import (
    categorize_with_keywords,
    JD_AREAS,
    JD_KEYWORDS,
)


class TestKeywordCategorization:
    """Tests for keyword-based categorization."""

    def test_categorize_receipt(self, sample_text_receipt: str):
        """Test that receipt text is categorized correctly."""
        result = categorize_with_keywords(sample_text_receipt)

        assert result is not None
        assert result["jd_area"] == "10-19 Finance"
        assert result["jd_category"] == "14 Receipts"
        assert result["confidence"] == "medium"

    def test_categorize_medical(self, sample_text_medical: str):
        """Test that medical document is categorized correctly."""
        result = categorize_with_keywords(sample_text_medical)

        assert result is not None
        assert result["jd_area"] == "20-29 Medical"
        assert result["jd_category"] == "21 Records"

    def test_categorize_contract(self, sample_text_contract: str):
        """Test that contract document is categorized correctly."""
        result = categorize_with_keywords(sample_text_contract)

        assert result is not None
        assert result["jd_area"] == "40-49 Work"
        assert result["jd_category"] == "41 Employment"

    def test_categorize_empty_text(self):
        """Test handling of empty text."""
        result = categorize_with_keywords("")

        # Should return some default or None
        assert result is not None
        # Default should be Finance/Banking or similar
        assert "jd_area" in result

    def test_categorize_unknown_content(self):
        """Test handling of text with no matching keywords."""
        result = categorize_with_keywords("random gibberish xyz abc 123")

        assert result is not None
        assert "jd_area" in result
        assert "jd_category" in result

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        result_lower = categorize_with_keywords("this is a receipt for purchase")
        result_upper = categorize_with_keywords("THIS IS A RECEIPT FOR PURCHASE")

        assert result_lower["jd_category"] == result_upper["jd_category"]

    def test_german_keywords(self):
        """Test German language keywords are matched."""
        german_text = "Rechnung für die Krankenversicherung TK"
        result = categorize_with_keywords(german_text)

        assert result is not None
        # Should match either Medical Insurance or Finance/Bills
        assert result["jd_area"] in ["20-29 Medical", "10-19 Finance"]


class TestJDStructure:
    """Tests for Johnny.Decimal structure constants."""

    def test_jd_areas_structure(self):
        """Test that JD_AREAS has the expected structure."""
        assert "00-09 System" in JD_AREAS
        assert "10-19 Finance" in JD_AREAS
        assert "20-29 Medical" in JD_AREAS
        assert "30-39 Legal" in JD_AREAS
        assert "40-49 Work" in JD_AREAS
        assert "50-59 Personal" in JD_AREAS

    def test_each_area_has_categories(self):
        """Test that each area has at least one category."""
        for area, categories in JD_AREAS.items():
            assert len(categories) > 0, f"Area {area} has no categories"
            for cat, config in categories.items():
                assert "keywords" in config, f"Category {cat} missing keywords"

    def test_jd_keywords_populated(self):
        """Test that JD_KEYWORDS is properly populated from JD_AREAS."""
        assert len(JD_KEYWORDS) > 0
        for (area, category), keywords in JD_KEYWORDS.items():
            assert area in JD_AREAS
            assert category in JD_AREAS[area]


class TestLLMCategorization:
    """Tests for LLM-based categorization (mocked)."""

    @patch("document_organizer.anthropic")
    def test_categorize_with_llm_success(
        self,
        mock_anthropic,
        sample_text_receipt: str,
        sample_analysis_json: dict,
    ):
        """Test successful LLM categorization."""
        # Setup mock
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(sample_analysis_json))]
        mock_client.messages.create.return_value = mock_response

        from document_organizer import categorize_with_llm

        result = categorize_with_llm(
            sample_text_receipt,
            api_key="test-key"
        )

        assert result is not None
        assert result["jd_area"] == "10-19 Finance"
        assert result["jd_category"] == "14 Receipts"

    def test_categorize_with_llm_no_api_key(self, sample_text_receipt: str):
        """Test fallback to keywords when no API key is provided."""
        from document_organizer import categorize_with_llm

        # Clear any existing API key
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)

        result = categorize_with_llm(sample_text_receipt, api_key=None)

        # Should fall back to keyword matching
        assert result is not None
        assert "jd_area" in result

    @patch("document_organizer.anthropic")
    def test_categorize_with_llm_api_error(
        self,
        mock_anthropic,
        sample_text_receipt: str,
    ):
        """Test fallback to keywords on API error."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        from document_organizer import categorize_with_llm

        result = categorize_with_llm(
            sample_text_receipt,
            api_key="test-key"
        )

        # Should fall back to keyword matching
        assert result is not None
        assert "jd_area" in result
