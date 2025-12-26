#!/usr/bin/env python3
"""
JD Builder - AI-Assisted Johnny Decimal System Builder

This module provides builders for creating personalized JD systems:
- InterviewBuilder: Conversational AI-guided system design
- WizardBuilder: Template-based quick setup (future)
- DocumentAnalysisBuilder: Learn from existing documents (future)
"""

import json
from pathlib import Path
from typing import Optional

from jd_system import JDSystem, JDValidator
from jd_prompts import (
    INTERVIEW_SYSTEM_PROMPT,
    INTERVIEW_INITIAL_MESSAGE,
    parse_structure_from_response
)


# ==============================================================================
# INTERVIEW BUILDER
# ==============================================================================

class InterviewBuilder:
    """Conversational JD system builder using AI.

    Guides users through a conversation to understand their document
    organization needs, then proposes a personalized JD structure.
    """

    def __init__(self, output_dir: str | Path):
        """Initialize the interview builder.

        Args:
            output_dir: The JD output directory where the system will be created
        """
        self.output_dir = Path(output_dir)
        self.conversation: list[dict] = []
        self.proposed_structure: dict | None = None
        self.user_context: dict = {}
        self._ai_provider = None

    @property
    def initial_message(self) -> str:
        """Get the initial AI greeting message."""
        return INTERVIEW_INITIAL_MESSAGE

    @property
    def has_proposal(self) -> bool:
        """Check if a structure has been proposed."""
        return self.proposed_structure is not None

    def set_ai_provider(self, provider):
        """Set the AI provider to use for chat.

        Args:
            provider: An AIProvider instance with chat() method
        """
        self._ai_provider = provider

    def get_conversation_for_display(self) -> list[dict]:
        """Get the conversation history for UI display.

        Returns:
            List of messages with role and content
        """
        if not self.conversation:
            # Return initial greeting if no conversation yet
            return [{"role": "assistant", "content": self.initial_message}]
        return self.conversation.copy()

    def process_message(self, user_input: str) -> dict:
        """Process a user message and get AI response.

        Args:
            user_input: The user's message

        Returns:
            Dict with:
            - type: "question" (more conversation needed) or "proposal" (structure ready)
            - message: AI response text (for questions)
            - structure: Proposed JD structure (for proposals)
            - reasoning: AI's reasoning for the proposal
        """
        if not self._ai_provider:
            return {
                "type": "error",
                "message": "No AI provider configured. Please set up an AI provider first."
            }

        # Add user message to conversation
        self.conversation.append({"role": "user", "content": user_input})

        try:
            # Get AI response
            response = self._ai_provider.chat(
                system_prompt=INTERVIEW_SYSTEM_PROMPT,
                messages=self.conversation
            )

            if not response:
                return {
                    "type": "error",
                    "message": "Failed to get response from AI. Please try again."
                }

            # Check if response contains a structure proposal
            proposal = parse_structure_from_response(response)

            if proposal and proposal.get("ready"):
                # AI has proposed a structure
                self.proposed_structure = proposal.get("structure", {})
                self.conversation.append({"role": "assistant", "content": response})

                return {
                    "type": "proposal",
                    "structure": self.proposed_structure,
                    "reasoning": proposal.get("reasoning", ""),
                    "message": response
                }
            else:
                # AI is asking more questions
                self.conversation.append({"role": "assistant", "content": response})

                return {
                    "type": "question",
                    "message": response
                }

        except Exception as e:
            return {
                "type": "error",
                "message": f"Error processing message: {str(e)}"
            }

    def modify_proposal(self, modifications: dict) -> dict:
        """Apply modifications to the proposed structure.

        Args:
            modifications: Dict with structure modifications

        Returns:
            Updated structure
        """
        if not self.proposed_structure:
            return {}

        # Deep merge modifications
        for area_name, area_data in modifications.items():
            if area_name in self.proposed_structure:
                if "categories" in area_data:
                    self.proposed_structure[area_name]["categories"].update(
                        area_data["categories"]
                    )
            else:
                self.proposed_structure[area_name] = area_data

        return self.proposed_structure

    def validate_proposal(self) -> tuple[bool, list[str]]:
        """Validate the proposed structure.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not self.proposed_structure:
            return False, ["No structure has been proposed yet"]

        return JDValidator.validate_structure(self.proposed_structure)

    def finalize(self, user_context: dict = None) -> JDSystem | None:
        """Create the JD system from the proposal.

        Args:
            user_context: Optional user context to store

        Returns:
            JDSystem instance if successful, None otherwise
        """
        if not self.proposed_structure:
            print("No structure to finalize")
            return None

        # Validate first
        is_valid, errors = self.validate_proposal()
        if not is_valid:
            print(f"Validation errors: {errors}")
            return None

        # Ensure System area exists
        if "00-09 System" not in self.proposed_structure:
            self.proposed_structure["00-09 System"] = {
                "description": "System folders",
                "categories": {
                    "00 Index": {
                        "description": "Master index",
                        "keywords": []
                    },
                    "01 Inbox": {
                        "description": "Incoming documents",
                        "keywords": []
                    }
                }
            }

        # Create JDSystem
        system = JDSystem(self.output_dir)
        success = system.create_from_structure(
            areas=self.proposed_structure,
            generation_method="interview",
            user_context=user_context or self.user_context
        )

        if success:
            # Create folder structure
            system.create_folders()
            return system

        return None

    def reset(self):
        """Reset the builder to start a new interview."""
        self.conversation = []
        self.proposed_structure = None
        self.user_context = {}


# ==============================================================================
# WIZARD BUILDER (FUTURE)
# ==============================================================================

class WizardBuilder:
    """Template-based JD system builder.

    Provides predefined templates that users can customize.
    """

    # Predefined templates for common use cases
    TEMPLATES = {
        "personal": {
            "name": "Personal Life Admin",
            "description": "For managing personal documents, finances, and life admin",
            "areas": {
                "00-09 System": {
                    "description": "System folders",
                    "categories": {
                        "00 Index": {"description": "Master index", "keywords": []},
                        "01 Inbox": {"description": "Incoming documents", "keywords": []}
                    }
                },
                "10-19 Finance": {
                    "description": "Personal finances",
                    "categories": {
                        "11 Banking": {"description": "Bank statements", "keywords": ["bank", "statement", "account"]},
                        "12 Taxes": {"description": "Tax documents", "keywords": ["tax", "return"]},
                        "13 Insurance": {"description": "Insurance policies", "keywords": ["insurance", "policy"]},
                        "14 Receipts": {"description": "Purchase receipts", "keywords": ["receipt", "purchase"]}
                    }
                },
                "20-29 Medical": {
                    "description": "Health and medical",
                    "categories": {
                        "21 Records": {"description": "Medical records", "keywords": ["doctor", "medical", "hospital"]},
                        "22 Insurance": {"description": "Health insurance", "keywords": ["health insurance"]}
                    }
                },
                "30-39 Legal": {
                    "description": "Legal documents",
                    "categories": {
                        "31 Contracts": {"description": "Contracts and agreements", "keywords": ["contract", "agreement"]},
                        "32 Identity": {"description": "ID documents", "keywords": ["passport", "id", "license"]}
                    }
                }
            }
        },
        "freelance": {
            "name": "Freelancer / Self-Employed",
            "description": "For freelancers managing personal and business documents",
            "areas": {
                "00-09 System": {
                    "description": "System folders",
                    "categories": {
                        "00 Index": {"description": "Master index", "keywords": []},
                        "01 Inbox": {"description": "Incoming documents", "keywords": []}
                    }
                },
                "10-19 Personal Finance": {
                    "description": "Personal finances",
                    "categories": {
                        "11 Banking": {"description": "Personal bank accounts", "keywords": ["bank", "personal"]},
                        "12 Taxes": {"description": "Personal taxes", "keywords": ["tax", "personal"]}
                    }
                },
                "20-29 Business": {
                    "description": "Business operations",
                    "categories": {
                        "21 Clients": {"description": "Client documents", "keywords": ["client", "customer"]},
                        "22 Invoices": {"description": "Invoices sent", "keywords": ["invoice", "billing"]},
                        "23 Expenses": {"description": "Business expenses", "keywords": ["expense", "receipt"]},
                        "24 Contracts": {"description": "Business contracts", "keywords": ["contract", "agreement"]},
                        "25 Taxes": {"description": "Business taxes", "keywords": ["business tax", "vat"]}
                    }
                },
                "30-39 Medical": {
                    "description": "Health documents",
                    "categories": {
                        "31 Records": {"description": "Medical records", "keywords": ["medical", "doctor"]}
                    }
                }
            }
        },
        "employee": {
            "name": "Employee",
            "description": "For employees managing work and personal documents",
            "areas": {
                "00-09 System": {
                    "description": "System folders",
                    "categories": {
                        "00 Index": {"description": "Master index", "keywords": []},
                        "01 Inbox": {"description": "Incoming documents", "keywords": []}
                    }
                },
                "10-19 Finance": {
                    "description": "Personal finances",
                    "categories": {
                        "11 Banking": {"description": "Bank statements", "keywords": ["bank", "statement"]},
                        "12 Taxes": {"description": "Tax documents", "keywords": ["tax", "return"]},
                        "13 Insurance": {"description": "Insurance", "keywords": ["insurance"]},
                        "14 Receipts": {"description": "Receipts", "keywords": ["receipt"]}
                    }
                },
                "20-29 Work": {
                    "description": "Employment documents",
                    "categories": {
                        "21 Employment": {"description": "Job contracts and HR", "keywords": ["employment", "contract", "hr"]},
                        "22 Salary": {"description": "Pay slips and bonuses", "keywords": ["salary", "payslip", "bonus"]},
                        "23 Expenses": {"description": "Work expenses", "keywords": ["expense", "reimbursement"]},
                        "24 Training": {"description": "Training and certifications", "keywords": ["training", "certificate"]}
                    }
                },
                "30-39 Medical": {
                    "description": "Health documents",
                    "categories": {
                        "31 Records": {"description": "Medical records", "keywords": ["medical", "doctor"]},
                        "32 Insurance": {"description": "Health insurance", "keywords": ["health insurance"]}
                    }
                }
            }
        }
    }

    def __init__(self, output_dir: str | Path):
        """Initialize the wizard builder."""
        self.output_dir = Path(output_dir)
        self.selected_template: str | None = None
        self.customizations: dict = {}

    @classmethod
    def get_templates(cls) -> dict:
        """Get available templates."""
        return {
            key: {
                "name": template["name"],
                "description": template["description"]
            }
            for key, template in cls.TEMPLATES.items()
        }

    def select_template(self, template_key: str) -> bool:
        """Select a template to use."""
        if template_key not in self.TEMPLATES:
            return False
        self.selected_template = template_key
        return True

    def get_structure(self) -> dict | None:
        """Get the current structure with customizations applied."""
        if not self.selected_template:
            return None

        import copy
        structure = copy.deepcopy(self.TEMPLATES[self.selected_template]["areas"])

        # Apply customizations
        for area_name, area_data in self.customizations.items():
            if area_name in structure:
                if "categories" in area_data:
                    structure[area_name]["categories"].update(area_data["categories"])
            else:
                structure[area_name] = area_data

        return structure

    def customize(self, modifications: dict):
        """Apply customizations to the template."""
        self.customizations.update(modifications)

    def finalize(self) -> JDSystem | None:
        """Create the JD system from the template."""
        structure = self.get_structure()
        if not structure:
            return None

        # Validate
        is_valid, errors = JDValidator.validate_structure(structure)
        if not is_valid:
            print(f"Validation errors: {errors}")
            return None

        # Create system
        system = JDSystem(self.output_dir)
        success = system.create_from_structure(
            areas=structure,
            generation_method="wizard",
            user_context={"template": self.selected_template}
        )

        if success:
            system.create_folders()
            return system

        return None


# ==============================================================================
# DOCUMENT ANALYSIS BUILDER (FUTURE)
# ==============================================================================

class DocumentAnalysisBuilder:
    """JD system builder that learns from existing documents.

    Analyzes a batch of documents to infer an optimal JD structure.
    """

    def __init__(self, output_dir: str | Path):
        """Initialize the document analysis builder."""
        self.output_dir = Path(output_dir)
        self.analyzed_documents: list = []
        self.proposed_structure: dict | None = None
        self._ai_provider = None

    def set_ai_provider(self, provider):
        """Set the AI provider to use."""
        self._ai_provider = provider

    def add_folder(self, folder_path: str | Path) -> int:
        """Add a folder of documents to analyze.

        Args:
            folder_path: Path to folder with documents

        Returns:
            Number of documents found
        """
        from document_organizer import SUPPORTED_FORMATS

        folder = Path(folder_path)
        if not folder.exists():
            return 0

        count = 0
        for file_path in folder.rglob("*"):
            if file_path.suffix.lower() in SUPPORTED_FORMATS:
                self.analyzed_documents.append(str(file_path))
                count += 1

        return count

    def analyze(self, progress_callback=None) -> dict | None:
        """Analyze documents and propose a structure.

        Args:
            progress_callback: Optional callback(current, total, filename)

        Returns:
            Proposed structure or None
        """
        # This will be implemented in a future phase
        # For now, return None
        return None

    def finalize(self) -> JDSystem | None:
        """Create the JD system from analysis."""
        if not self.proposed_structure:
            return None

        # Validate
        is_valid, errors = JDValidator.validate_structure(self.proposed_structure)
        if not is_valid:
            print(f"Validation errors: {errors}")
            return None

        # Create system
        system = JDSystem(self.output_dir)
        success = system.create_from_structure(
            areas=self.proposed_structure,
            generation_method="document_analysis",
            user_context={"documents_analyzed": len(self.analyzed_documents)}
        )

        if success:
            system.create_folders()
            return system

        return None
