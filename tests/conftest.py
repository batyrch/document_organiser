"""
Pytest configuration and shared fixtures for Document Organizer tests.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def inbox_dir(temp_dir: Path) -> Path:
    """Create a temporary inbox directory."""
    inbox = temp_dir / "inbox"
    inbox.mkdir()
    return inbox


@pytest.fixture
def output_dir(temp_dir: Path) -> Path:
    """Create a temporary output directory with JD structure."""
    output = temp_dir / "jd_documents"
    output.mkdir()
    # Create basic JD structure
    (output / "00-09 System" / "01 Inbox").mkdir(parents=True)
    (output / "10-19 Finance" / "14 Receipts").mkdir(parents=True)
    (output / "20-29 Medical" / "21 Records").mkdir(parents=True)
    return output


@pytest.fixture
def sample_text_receipt() -> str:
    """Sample text from a receipt document."""
    return """
    AMAZON.DE
    Order #123-4567890-1234567

    Order Date: December 20, 2024

    Item: Apple MacBook Pro 14" M3
    Price: €2,499.00

    Shipping: FREE
    Tax: €398.41

    Total: €2,897.41

    Payment Method: Visa ending in 1234

    Thank you for your purchase!
    """


@pytest.fixture
def sample_text_medical() -> str:
    """Sample text from a medical document."""
    return """
    CHARITÉ UNIVERSITÄTSMEDIZIN BERLIN

    Laboratory Results
    Patient ID: 12345678
    Date: 2024-12-15

    Blood Test Results:

    Hemoglobin: 14.2 g/dL (Normal: 12-16)
    White Blood Cells: 7,500 /µL (Normal: 4,500-11,000)
    Platelets: 250,000 /µL (Normal: 150,000-400,000)

    Glucose (fasting): 95 mg/dL (Normal: 70-100)

    Physician: Dr. Maria Schmidt
    """


@pytest.fixture
def sample_text_contract() -> str:
    """Sample text from a contract document."""
    return """
    EMPLOYMENT CONTRACT

    Between:
    AutoScout24 GmbH ("Employer")
    Rosenheimer Str. 123
    81667 Munich, Germany

    And:
    [Employee Name] ("Employee")

    Effective Date: January 1, 2024

    Position: Senior Software Engineer
    Annual Salary: €85,000

    Terms and Conditions...
    """


@pytest.fixture
def sample_analysis_json() -> dict:
    """Sample analysis JSON as returned by Claude."""
    return {
        "jd_area": "10-19 Finance",
        "jd_category": "14 Receipts",
        "document_type": "Laptop Receipt",
        "issuer": "Amazon",
        "subject_person": None,
        "tags": ["receipt", "electronics", "laptop"],
        "confidence": "high",
        "summary": "Amazon receipt for MacBook Pro laptop purchase",
        "date_mentioned": "2024-12-20",
        "entities": ["Amazon.de", "Apple MacBook Pro"]
    }


@pytest.fixture
def sample_metadata_json() -> dict:
    """Sample metadata JSON stored with organized files."""
    return {
        "id": "14.01",
        "jd_area": "10-19 Finance",
        "jd_category": "14 Receipts",
        "document_type": "Laptop Receipt",
        "issuer": "Amazon",
        "subject_person": None,
        "document_date": "2024-12-20",
        "tags": ["receipt", "electronics"],
        "summary": "Amazon receipt for MacBook Pro purchase",
        "extracted_text": "AMAZON.DE Order #123..."
    }


@pytest.fixture
def mock_claude_response(sample_analysis_json: dict):
    """Mock Claude API response."""
    mock = MagicMock()
    mock.content = [MagicMock(text=json.dumps(sample_analysis_json))]
    return mock


@pytest.fixture
def sample_pdf_path(inbox_dir: Path) -> Path:
    """Create a minimal test PDF file."""
    # Create a simple text file as placeholder (actual PDF testing would need a real PDF)
    pdf_path = inbox_dir / "test_receipt.pdf"
    pdf_path.write_text("This is a placeholder for PDF content")
    return pdf_path


@pytest.fixture
def sample_image_path(inbox_dir: Path) -> Path:
    """Create a minimal test image file."""
    from PIL import Image

    img_path = inbox_dir / "test_document.png"
    # Create a simple 100x100 white image
    img = Image.new('RGB', (100, 100), color='white')
    img.save(img_path)
    return img_path


@pytest.fixture(autouse=True)
def reset_env_vars():
    """Reset environment variables before each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def env_with_paths(temp_dir: Path, inbox_dir: Path, output_dir: Path):
    """Set up environment variables for testing."""
    os.environ["INBOX_DIR"] = str(inbox_dir)
    os.environ["OUTPUT_DIR"] = str(output_dir)
    os.environ["LOG_LEVEL"] = "DEBUG"
    return {
        "inbox": inbox_dir,
        "output": output_dir,
    }
