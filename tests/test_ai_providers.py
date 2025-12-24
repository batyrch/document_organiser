"""
Tests for the AI providers module.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_providers import (
    AIProvider,
    AnthropicProvider,
    ClaudeCodeProvider,
    OpenAIProvider,
    BedrockProvider,
    OllamaProvider,
    KeywordProvider,
    list_providers,
    get_provider,
    categorize_document,
    PROVIDERS,
)


# Sample JD areas for testing
SAMPLE_JD_AREAS = {
    "10-19 Finance": {
        "14 Receipts": {"keywords": ["receipt", "purchase", "bought"]},
        "16 Bills": {"keywords": ["invoice", "bill", "payment"]},
    },
    "20-29 Medical": {
        "21 Records": {"keywords": ["medical", "doctor", "hospital", "blood", "test"]},
    },
}


class TestAIProviderBase:
    """Tests for the base AIProvider class."""

    def test_get_categorization_prompt(self):
        """Test prompt generation."""
        provider = KeywordProvider()  # Use concrete implementation
        prompt = provider.get_categorization_prompt("Test document", SAMPLE_JD_AREAS)

        assert "Johnny.Decimal" in prompt
        assert "Test document" in prompt
        assert "10-19 Finance" in prompt
        assert "jd_area" in prompt

    def test_parse_json_response_clean(self):
        """Test parsing clean JSON response."""
        provider = KeywordProvider()
        response = '{"jd_area": "10-19 Finance", "jd_category": "14 Receipts"}'

        result = provider.parse_json_response(response)

        assert result["jd_area"] == "10-19 Finance"

    def test_parse_json_response_with_code_block(self):
        """Test parsing JSON wrapped in code blocks."""
        provider = KeywordProvider()
        response = '''```json
{"jd_area": "10-19 Finance", "jd_category": "14 Receipts"}
```'''

        result = provider.parse_json_response(response)

        assert result["jd_area"] == "10-19 Finance"

    def test_parse_json_response_invalid(self):
        """Test parsing invalid JSON."""
        provider = KeywordProvider()
        response = "This is not JSON"

        result = provider.parse_json_response(response)

        assert result is None


class TestKeywordProvider:
    """Tests for KeywordProvider."""

    def test_is_available(self):
        """Test that keyword provider is always available."""
        provider = KeywordProvider()
        assert provider.is_available() is True

    def test_categorize_receipt(self):
        """Test categorizing receipt text."""
        provider = KeywordProvider()
        result = provider.categorize("This is a receipt for purchase", SAMPLE_JD_AREAS)

        assert result is not None
        assert result["jd_area"] == "10-19 Finance"
        assert result["jd_category"] == "14 Receipts"

    def test_categorize_medical(self):
        """Test categorizing medical text."""
        provider = KeywordProvider()
        result = provider.categorize("Blood test results from hospital", SAMPLE_JD_AREAS)

        assert result is not None
        assert result["jd_area"] == "20-29 Medical"
        assert result["jd_category"] == "21 Records"

    def test_categorize_empty_text(self):
        """Test categorizing empty text."""
        provider = KeywordProvider()
        result = provider.categorize("", SAMPLE_JD_AREAS)

        # Should return a default category
        assert result is not None
        assert "jd_area" in result


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def test_is_available_with_key(self):
        """Test availability with API key."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_is_available_without_key(self):
        """Test availability without API key."""
        os.environ.pop("ANTHROPIC_API_KEY", None)
        provider = AnthropicProvider(api_key=None)
        assert provider.is_available() is False

    @patch("ai_providers.anthropic")
    def test_categorize_success(self, mock_anthropic):
        """Test successful categorization."""
        # Setup mock
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            text='{"jd_area": "10-19 Finance", "jd_category": "14 Receipts"}'
        )]
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider(api_key="test-key")
        result = provider.categorize("Receipt text", SAMPLE_JD_AREAS)

        assert result is not None
        assert result["jd_area"] == "10-19 Finance"

    @patch("ai_providers.anthropic")
    def test_categorize_api_error(self, mock_anthropic):
        """Test handling API errors."""
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        provider = AnthropicProvider(api_key="test-key")
        result = provider.categorize("Receipt text", SAMPLE_JD_AREAS)

        assert result is None


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def test_is_available_with_key(self):
        """Test availability with API key."""
        provider = OpenAIProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_is_available_without_key(self):
        """Test availability without API key."""
        os.environ.pop("OPENAI_API_KEY", None)
        provider = OpenAIProvider(api_key=None)
        assert provider.is_available() is False

    @patch("ai_providers.OpenAI")
    def test_categorize_success(self, mock_openai_class):
        """Test successful categorization."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(
            message=MagicMock(content='{"jd_area": "10-19 Finance", "jd_category": "14 Receipts"}')
        )]
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider(api_key="test-key")
        result = provider.categorize("Receipt text", SAMPLE_JD_AREAS)

        assert result is not None
        assert result["jd_area"] == "10-19 Finance"


class TestClaudeCodeProvider:
    """Tests for ClaudeCodeProvider."""

    @patch("subprocess.run")
    def test_is_available_installed(self, mock_run):
        """Test availability when Claude CLI is installed."""
        mock_run.return_value = MagicMock(returncode=0)

        provider = ClaudeCodeProvider()
        assert provider.is_available() is True

    @patch("subprocess.run")
    def test_is_available_not_installed(self, mock_run):
        """Test availability when Claude CLI is not installed."""
        mock_run.side_effect = FileNotFoundError()

        provider = ClaudeCodeProvider()
        assert provider.is_available() is False

    @patch("subprocess.run")
    def test_categorize_success(self, mock_run):
        """Test successful categorization via CLI."""
        # Mock version check
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Version check
            MagicMock(
                returncode=0,
                stdout='{"jd_area": "10-19 Finance", "jd_category": "14 Receipts"}'
            )
        ]

        provider = ClaudeCodeProvider()
        result = provider.categorize("Receipt text", SAMPLE_JD_AREAS)

        assert result is not None
        assert result["jd_area"] == "10-19 Finance"


class TestBedrockProvider:
    """Tests for BedrockProvider."""

    def test_model_aliases(self):
        """Test that model aliases are defined."""
        provider = BedrockProvider(model="claude-3-sonnet")
        assert "anthropic" in provider.model_id

    @patch("ai_providers.boto3")
    def test_is_available_with_credentials(self, mock_boto3):
        """Test availability with AWS credentials."""
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_session.get_credentials.return_value = MagicMock()

        provider = BedrockProvider()
        assert provider.is_available() is True

    @patch("ai_providers.boto3")
    def test_is_available_without_credentials(self, mock_boto3):
        """Test availability without AWS credentials."""
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_session.get_credentials.return_value = None

        provider = BedrockProvider()
        assert provider.is_available() is False


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    @patch("ai_providers.requests")
    def test_is_available_running(self, mock_requests):
        """Test availability when Ollama is running."""
        mock_requests.get.return_value = MagicMock(status_code=200)

        provider = OllamaProvider()
        assert provider.is_available() is True

    @patch("ai_providers.requests")
    def test_is_available_not_running(self, mock_requests):
        """Test availability when Ollama is not running."""
        mock_requests.get.side_effect = Exception("Connection refused")

        provider = OllamaProvider()
        assert provider.is_available() is False


class TestProviderRegistry:
    """Tests for provider registry functions."""

    def test_list_providers(self):
        """Test listing all providers."""
        providers = list_providers()

        assert "anthropic" in providers
        assert "openai" in providers
        assert "bedrock" in providers
        assert "ollama" in providers
        assert "keywords" in providers
        assert "claude-code" in providers

        # Check structure
        for name, info in providers.items():
            assert "display_name" in info
            assert "requires_api_key" in info
            assert "available" in info

    def test_get_provider_by_name(self):
        """Test getting a provider by name."""
        provider = get_provider("keywords")
        assert isinstance(provider, KeywordProvider)

    def test_get_provider_invalid_name(self):
        """Test getting an invalid provider."""
        with pytest.raises(ValueError):
            get_provider("nonexistent_provider")

    def test_get_provider_auto_detect(self):
        """Test auto-detection when no name provided."""
        os.environ.pop("AI_PROVIDER", None)
        provider = get_provider()

        # Should return some provider (at minimum, keywords)
        assert isinstance(provider, AIProvider)


class TestCategorizeDocument:
    """Tests for the categorize_document helper function."""

    def test_categorize_with_keywords(self):
        """Test categorization using keyword provider."""
        result = categorize_document(
            "This is a receipt for purchase",
            SAMPLE_JD_AREAS,
            provider="keywords"
        )

        assert result is not None
        assert result["jd_area"] == "10-19 Finance"

    def test_categorize_with_fallback(self):
        """Test fallback to keywords on provider failure."""
        result = categorize_document(
            "Medical blood test results",
            SAMPLE_JD_AREAS,
            provider="anthropic",  # Will fail without key
            fallback_to_keywords=True
        )

        # Should fall back to keywords
        assert result is not None

    def test_categorize_without_fallback(self):
        """Test no fallback when disabled."""
        os.environ.pop("ANTHROPIC_API_KEY", None)
        result = categorize_document(
            "Medical blood test results",
            SAMPLE_JD_AREAS,
            provider="anthropic",
            fallback_to_keywords=False
        )

        # Should return None without fallback
        assert result is None
