#!/usr/bin/env python3
"""
AI Provider Module - Pluggable AI backends for document categorization.

Supports multiple AI providers:
- Anthropic Claude (API and Claude Code CLI)
- OpenAI (GPT-4, GPT-3.5)
- AWS Bedrock (Claude, Titan, etc.)
- Local/Ollama (for offline use)

Usage:
    from ai_providers import get_provider, list_providers

    # Get a provider by name
    provider = get_provider("anthropic")
    result = provider.categorize(text, jd_areas)

    # Or use environment-based auto-detection
    provider = get_provider()  # Uses AI_PROVIDER env var
"""

import json
import os
import re
import subprocess
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file (if it exists and is accessible)
# In bundled apps, API keys are stored in OS keychain via settings.py instead
try:
    load_dotenv()
except (PermissionError, OSError):
    pass  # .env not accessible, likely running as bundled app


# ==============================================================================
# BASE PROVIDER CLASS
# ==============================================================================

class AIProvider(ABC):
    """Abstract base class for AI providers."""

    name: str = "base"
    display_name: str = "Base Provider"
    requires_api_key: bool = True

    @abstractmethod
    def categorize(self, text: str, jd_areas: dict) -> Optional[dict]:
        """
        Categorize document text using the AI provider.

        Args:
            text: Extracted document text
            jd_areas: Johnny.Decimal areas and categories structure

        Returns:
            Dictionary with categorization results or None on failure
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        pass

    def chat(self, system_prompt: str, messages: list) -> Optional[str]:
        """
        Have a multi-turn conversation with the AI.

        Args:
            system_prompt: The system prompt to guide the AI
            messages: List of {"role": "user"|"assistant", "content": str}

        Returns:
            The AI's response text or None on failure
        """
        # Default implementation - subclasses should override
        return None

    def get_categorization_prompt(self, text: str, jd_areas: dict) -> str:
        """Generate the categorization prompt for any provider."""
        # Truncate text if too long
        max_chars = 8000
        truncated_text = text[:max_chars] if len(text) > max_chars else text

        # Build JD structure for prompt (exclude system and archive areas)
        jd_structure = {}
        for area, categories in jd_areas.items():
            if area not in ["00-09 System", "90-99 Archive"]:
                jd_structure[area] = list(categories.keys())

        return f"""You are a document categorization assistant using the Johnny.Decimal system.

Available Johnny.Decimal areas and categories:
{json.dumps(jd_structure, indent=2)}

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

    def parse_json_response(self, response_text: str) -> Optional[dict]:
        """Parse JSON from AI response, handling code blocks."""
        try:
            text = response_text.strip()

            # Handle markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            # Try to find JSON object
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group()

            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return None


# ==============================================================================
# ANTHROPIC PROVIDER
# ==============================================================================

class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    name = "anthropic"
    display_name = "Anthropic Claude"
    requires_api_key = True

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def categorize(self, text: str, jd_areas: dict) -> Optional[dict]:
        if not self.is_available():
            return None

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            prompt = self.get_categorization_prompt(text, jd_areas)

            response = client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            return self.parse_json_response(response.content[0].text)

        except Exception as e:
            print(f"Anthropic API error: {e}")
            return None

    def chat(self, system_prompt: str, messages: list) -> Optional[str]:
        """Have a multi-turn conversation with Claude."""
        if not self.is_available():
            return None

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            response = client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=messages
            )

            return response.content[0].text

        except Exception as e:
            print(f"Anthropic chat error: {e}")
            return None


class ClaudeCodeProvider(AIProvider):
    """Claude Code CLI provider (uses Max subscription)."""

    name = "claude-code"
    display_name = "Claude Code CLI"
    requires_api_key = False

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def categorize(self, text: str, jd_areas: dict) -> Optional[dict]:
        if not self.is_available():
            return None

        try:
            prompt = self.get_categorization_prompt(text, jd_areas)

            result = subprocess.run(
                ["claude", "--print", prompt],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return None

            return self.parse_json_response(result.stdout)

        except (subprocess.TimeoutExpired, Exception) as e:
            print(f"Claude Code CLI error: {e}")
            return None


# ==============================================================================
# OPENAI PROVIDER
# ==============================================================================

class OpenAIProvider(AIProvider):
    """OpenAI GPT provider."""

    name = "openai"
    display_name = "OpenAI GPT"
    requires_api_key = True

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def categorize(self, text: str, jd_areas: dict) -> Optional[dict]:
        if not self.is_available():
            return None

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            prompt = self.get_categorization_prompt(text, jd_areas)

            response = client.chat.completions.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            return self.parse_json_response(response.choices[0].message.content)

        except ImportError:
            print("OpenAI package not installed. Run: pip install openai")
            return None
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None

    def chat(self, system_prompt: str, messages: list) -> Optional[str]:
        """Have a multi-turn conversation with GPT."""
        if not self.is_available():
            return None

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            # Build messages with system prompt
            chat_messages = [{"role": "system", "content": system_prompt}]
            chat_messages.extend(messages)

            response = client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                messages=chat_messages
            )

            return response.choices[0].message.content

        except ImportError:
            print("OpenAI package not installed. Run: pip install openai")
            return None
        except Exception as e:
            print(f"OpenAI chat error: {e}")
            return None


# ==============================================================================
# AWS BEDROCK PROVIDER
# ==============================================================================

class BedrockProvider(AIProvider):
    """AWS Bedrock provider (supports Claude, Titan, etc.)."""

    name = "bedrock"
    display_name = "AWS Bedrock"
    requires_api_key = False  # Uses AWS credentials

    # Supported models
    MODELS = {
        "claude-sonnet-4": "anthropic.claude-sonnet-4-20250514-v1:0",
        "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
        "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
        "claude-instant": "anthropic.claude-instant-v1",
        "titan-express": "amazon.titan-text-express-v1",
        "titan-lite": "amazon.titan-text-lite-v1",
    }

    def __init__(
        self,
        model: str = "claude-sonnet-4",
        region: Optional[str] = None,
        profile: Optional[str] = None
    ):
        self.model_alias = model
        self.model_id = self.MODELS.get(model, model)
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.profile = profile or os.getenv("AWS_PROFILE")

    def is_available(self) -> bool:
        try:
            import boto3
            # Check if credentials are configured
            session = boto3.Session(profile_name=self.profile) if self.profile else boto3.Session()
            credentials = session.get_credentials()
            return credentials is not None
        except ImportError:
            return False
        except Exception:
            return False

    def categorize(self, text: str, jd_areas: dict) -> Optional[dict]:
        if not self.is_available():
            return None

        try:
            import boto3

            session = boto3.Session(
                profile_name=self.profile,
                region_name=self.region
            ) if self.profile else boto3.Session(region_name=self.region)

            client = session.client("bedrock-runtime")
            prompt = self.get_categorization_prompt(text, jd_areas)

            # Format request based on model type
            if "anthropic" in self.model_id:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}]
                })
            elif "titan" in self.model_id:
                body = json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 500,
                        "temperature": 0.7,
                    }
                })
            else:
                # Generic format
                body = json.dumps({
                    "prompt": prompt,
                    "max_tokens": 500
                })

            response = client.invoke_model(
                modelId=self.model_id,
                body=body
            )

            response_body = json.loads(response["body"].read())

            # Extract text based on model type
            if "anthropic" in self.model_id:
                result_text = response_body["content"][0]["text"]
            elif "titan" in self.model_id:
                result_text = response_body["results"][0]["outputText"]
            else:
                result_text = str(response_body)

            return self.parse_json_response(result_text)

        except ImportError:
            print("boto3 package not installed. Run: pip install boto3")
            return None
        except Exception as e:
            print(f"AWS Bedrock error: {e}")
            return None


# ==============================================================================
# OLLAMA / LOCAL PROVIDER
# ==============================================================================

class OllamaProvider(AIProvider):
    """Ollama local LLM provider."""

    name = "ollama"
    display_name = "Ollama (Local)"
    requires_api_key = False

    # Allowed hosts for Ollama (security: prevent SSRF to arbitrary servers)
    ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434"
    ):
        self.model = model
        self.base_url = self._validate_url(base_url)

    def _validate_url(self, url: str) -> str:
        """Validate Ollama URL to prevent SSRF attacks."""
        from urllib.parse import urlparse
        parsed = urlparse(url)

        # Extract hostname (handle IPv6)
        hostname = parsed.hostname or ""

        # Only allow localhost connections
        if hostname not in self.ALLOWED_HOSTS:
            print(f"Warning: Ollama URL must be localhost. Got: {hostname}. Using default.")
            return "http://localhost:11434"

        return url

    def is_available(self) -> bool:
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def categorize(self, text: str, jd_areas: dict) -> Optional[dict]:
        if not self.is_available():
            return None

        try:
            import requests

            prompt = self.get_categorization_prompt(text, jd_areas)

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 500}
                },
                timeout=120
            )

            if response.status_code != 200:
                return None

            result = response.json()
            return self.parse_json_response(result.get("response", ""))

        except ImportError:
            print("requests package not installed. Run: pip install requests")
            return None
        except Exception as e:
            print(f"Ollama error: {e}")
            return None


# ==============================================================================
# KEYWORD PROVIDER (NO AI)
# ==============================================================================

class KeywordProvider(AIProvider):
    """Keyword-based categorization (no AI required)."""

    name = "keywords"
    display_name = "Keyword Matching (No AI)"
    requires_api_key = False

    def is_available(self) -> bool:
        return True  # Always available

    def categorize(self, text: str, jd_areas: dict) -> Optional[dict]:
        """Categorize using keyword matching."""
        text_lower = text.lower()

        best_match = None
        best_score = 0

        for area, categories in jd_areas.items():
            if area in ["00-09 System", "90-99 Archive"]:
                continue

            for category, config in categories.items():
                keywords = config.get("keywords", [])
                score = sum(1 for kw in keywords if kw.lower() in text_lower)

                if score > best_score:
                    best_score = score
                    best_match = (area, category)

        if best_match:
            return {
                "jd_area": best_match[0],
                "jd_category": best_match[1],
                "document_type": "Document",
                "issuer": "Unknown",
                "subject_person": None,
                "tags": [],
                "confidence": "low" if best_score < 2 else "medium",
                "summary": "Categorized by keyword matching",
                "date_mentioned": None,
                "entities": []
            }

        # Default to first non-system area
        for area, categories in jd_areas.items():
            if area not in ["00-09 System", "90-99 Archive"]:
                first_cat = list(categories.keys())[0]
                return {
                    "jd_area": area,
                    "jd_category": first_cat,
                    "document_type": "Document",
                    "issuer": "Unknown",
                    "subject_person": None,
                    "tags": [],
                    "confidence": "low",
                    "summary": "Default categorization",
                    "date_mentioned": None,
                    "entities": []
                }

        return None


# ==============================================================================
# PROVIDER REGISTRY
# ==============================================================================

# Registry of all available providers
PROVIDERS = {
    "anthropic": AnthropicProvider,
    "claude-code": ClaudeCodeProvider,
    "openai": OpenAIProvider,
    "bedrock": BedrockProvider,
    "ollama": OllamaProvider,
    "keywords": KeywordProvider,
}


def list_providers() -> dict:
    """List all available providers and their status."""
    result = {}
    for name, provider_class in PROVIDERS.items():
        provider = provider_class()
        result[name] = {
            "display_name": provider.display_name,
            "requires_api_key": provider.requires_api_key,
            "available": provider.is_available(),
        }
    return result


def get_provider(
    name: Optional[str] = None,
    **kwargs
) -> AIProvider:
    """
    Get an AI provider instance.

    Args:
        name: Provider name. If None, uses AI_PROVIDER env var or auto-detects.
        **kwargs: Provider-specific configuration options.

    Returns:
        An AIProvider instance.

    Raises:
        ValueError: If the specified provider is not found.
    """
    # Use environment variable if no name specified
    if name is None:
        name = os.getenv("AI_PROVIDER", "").lower()

    # Auto-detect if still no name
    if not name:
        # Try providers in order of preference
        for provider_name in ["claude-code", "anthropic", "openai", "bedrock", "ollama", "keywords"]:
            provider = PROVIDERS[provider_name](**kwargs) if kwargs else PROVIDERS[provider_name]()
            if provider.is_available():
                return provider
        # Fall back to keywords
        return KeywordProvider()

    # Get specific provider
    if name not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")

    return PROVIDERS[name](**kwargs) if kwargs else PROVIDERS[name]()


def categorize_document(
    text: str,
    jd_areas: dict,
    provider: Optional[str] = None,
    fallback_to_keywords: bool = True,
    **provider_kwargs
) -> Optional[dict]:
    """
    Categorize a document using the specified or auto-detected provider.

    Args:
        text: Document text to categorize.
        jd_areas: Johnny.Decimal areas structure.
        provider: Provider name (optional, auto-detects if None).
        fallback_to_keywords: If True, falls back to keywords on failure.
        **provider_kwargs: Additional provider configuration.

    Returns:
        Categorization result or None.
    """
    try:
        ai_provider = get_provider(provider, **provider_kwargs)
        result = ai_provider.categorize(text, jd_areas)

        if result:
            return result

        # Fallback to keywords
        if fallback_to_keywords and ai_provider.name != "keywords":
            return KeywordProvider().categorize(text, jd_areas)

        return None

    except Exception as e:
        print(f"Categorization error: {e}")
        if fallback_to_keywords:
            return KeywordProvider().categorize(text, jd_areas)
        return None
