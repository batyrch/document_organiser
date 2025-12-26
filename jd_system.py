#!/usr/bin/env python3
"""
JD System - Dynamic Johnny Decimal System Management

This module provides classes for managing a dynamic Johnny Decimal system
that can be personalized by users through AI-assisted building, stored in
jdex.json, and evolved over time with smart suggestions.

Key components:
- JDSystem: Load/save the JD structure from jdex.json
- JDValidator: Enforce JD constraints (max 10 areas, max 10 categories)
- Helper functions for system management
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import copy


# ==============================================================================
# JD VALIDATOR
# ==============================================================================

class JDValidator:
    """Enforces Johnny Decimal constraints on system structures."""

    MAX_AREAS = 10
    MAX_CATEGORIES_PER_AREA = 10
    RESERVED_AREA = "00-09"  # System area (Index, Inbox, etc.)

    # Valid area ranges (10-19, 20-29, ..., 90-99)
    VALID_AREA_RANGES = [
        (0, 9),    # 00-09 System (reserved)
        (10, 19),
        (20, 29),
        (30, 39),
        (40, 49),
        (50, 59),
        (60, 69),
        (70, 79),
        (80, 89),
        (90, 99),
    ]

    @classmethod
    def is_valid_area_name(cls, name: str) -> bool:
        """Check if a name follows the JD area pattern (e.g., '10-19 Finance')."""
        pattern = r'^\d{2}-\d{2}\s+.+'
        return bool(re.match(pattern, name))

    @classmethod
    def is_valid_category_name(cls, name: str) -> bool:
        """Check if a name follows the JD category pattern (e.g., '14 Receipts')."""
        pattern = r'^\d{2}\s+.+'
        return bool(re.match(pattern, name))

    @classmethod
    def get_area_range(cls, area_name: str) -> tuple[int, int] | None:
        """Extract numeric range from area name (e.g., '10-19 Finance' -> (10, 19))."""
        match = re.match(r'^(\d{2})-(\d{2})\s+', area_name)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None

    @classmethod
    def get_category_number(cls, category_name: str) -> int | None:
        """Extract category number from name (e.g., '14 Receipts' -> 14)."""
        match = re.match(r'^(\d{2})\s+', category_name)
        if match:
            return int(match.group(1))
        return None

    @classmethod
    def category_belongs_to_area(cls, category_name: str, area_name: str) -> bool:
        """Check if a category number falls within an area's range."""
        cat_num = cls.get_category_number(category_name)
        area_range = cls.get_area_range(area_name)
        if cat_num is None or area_range is None:
            return False
        return area_range[0] <= cat_num <= area_range[1]

    @classmethod
    def validate_structure(cls, areas: dict) -> tuple[bool, list[str]]:
        """Validate a JD structure against all constraints.

        Args:
            areas: Dict of area_name -> {categories: {...}, description: str}

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check area count (excluding system area from limit)
        non_system_areas = [a for a in areas if not a.startswith("00-09")]
        if len(non_system_areas) > cls.MAX_AREAS - 1:  # -1 because 00-09 is reserved
            errors.append(f"Too many areas: {len(non_system_areas)} (max {cls.MAX_AREAS - 1} user areas)")

        used_ranges = set()

        for area_name, area_data in areas.items():
            # Validate area name format
            if not cls.is_valid_area_name(area_name):
                errors.append(f"Invalid area name format: '{area_name}' (expected 'XX-XX Name')")
                continue

            # Check for duplicate area ranges
            area_range = cls.get_area_range(area_name)
            if area_range:
                range_key = (area_range[0], area_range[1])
                if range_key in used_ranges:
                    errors.append(f"Duplicate area range: {area_name}")
                used_ranges.add(range_key)

                # Check if range is valid
                if range_key not in [(r[0], r[1]) for r in cls.VALID_AREA_RANGES]:
                    errors.append(f"Invalid area range: {area_name} (must be X0-X9 pattern)")

            # Get categories
            categories = area_data.get("categories", {})
            if isinstance(area_data, dict) and "keywords" in area_data:
                # Old format: area_data is directly the categories
                categories = area_data

            # Check category count
            if len(categories) > cls.MAX_CATEGORIES_PER_AREA:
                errors.append(f"Too many categories in {area_name}: {len(categories)} (max {cls.MAX_CATEGORIES_PER_AREA})")

            used_numbers = set()

            for cat_name in categories:
                # Validate category name format
                if not cls.is_valid_category_name(cat_name):
                    errors.append(f"Invalid category name format: '{cat_name}' in {area_name}")
                    continue

                # Check category belongs to area
                if not cls.category_belongs_to_area(cat_name, area_name):
                    errors.append(f"Category {cat_name} outside range for {area_name}")

                # Check for duplicate category numbers within area
                cat_num = cls.get_category_number(cat_name)
                if cat_num in used_numbers:
                    errors.append(f"Duplicate category number {cat_num} in {area_name}")
                used_numbers.add(cat_num)

        return len(errors) == 0, errors

    @classmethod
    def suggest_next_category_number(cls, area_name: str, existing_categories: dict) -> int | None:
        """Suggest the next available category number in an area.

        Args:
            area_name: The area to find a slot in (e.g., '10-19 Finance')
            existing_categories: Dict of existing category names

        Returns:
            Next available number, or None if area is full
        """
        area_range = cls.get_area_range(area_name)
        if not area_range:
            return None

        used_numbers = set()
        for cat_name in existing_categories:
            num = cls.get_category_number(cat_name)
            if num is not None:
                used_numbers.add(num)

        # Find first available number in range
        for num in range(area_range[0], area_range[1] + 1):
            if num not in used_numbers:
                return num

        return None  # Area is full

    @classmethod
    def suggest_next_area_range(cls, existing_areas: dict) -> tuple[int, int] | None:
        """Suggest the next available area range.

        Returns:
            Next available range tuple (e.g., (60, 69)), or None if full
        """
        used_ranges = set()
        for area_name in existing_areas:
            r = cls.get_area_range(area_name)
            if r:
                used_ranges.add(r)

        for valid_range in cls.VALID_AREA_RANGES:
            if valid_range not in used_ranges:
                return valid_range

        return None  # All ranges used


# ==============================================================================
# JD SYSTEM
# ==============================================================================

class JDSystem:
    """Manages a dynamic Johnny Decimal system with persistence.

    The system is stored in jdex.json and includes:
    - areas: The JD structure (areas and categories)
    - meta: Creation info, user context, generation method
    - evolution: Tracking for suggestions and history
    - classification_stats: Confidence tracking per category
    """

    DEFAULT_JDEX_PATH = "00-09 System/00 Index/jdex.json"

    def __init__(self, output_dir: str | Path):
        """Initialize JDSystem for a given output directory.

        Args:
            output_dir: The root JD output directory
        """
        self.output_dir = Path(output_dir)
        self.jdex_path = self.output_dir / self.DEFAULT_JDEX_PATH

        # Initialize empty structure
        self._data = {
            "meta": {
                "version": "1.0",
                "created_at": None,
                "last_modified": None,
                "generation_method": None,
                "user_context": {}
            },
            "areas": {},
            "evolution": {
                "total_documents": 0,
                "last_review": None,
                "next_milestone": 100,
                "pending_suggestions": [],
                "history": []
            },
            "classification_stats": {
                "by_category": {},
                "low_confidence_patterns": []
            }
        }

        # Load existing jdex.json if it exists
        if self.jdex_path.exists():
            self.load()

    @property
    def exists(self) -> bool:
        """Check if a jdex.json file exists for this system."""
        return self.jdex_path.exists()

    @property
    def areas(self) -> dict:
        """Get the areas structure."""
        return self._data.get("areas", {})

    @areas.setter
    def areas(self, value: dict):
        """Set the areas structure."""
        self._data["areas"] = value

    @property
    def meta(self) -> dict:
        """Get the metadata."""
        return self._data.get("meta", {})

    @property
    def evolution(self) -> dict:
        """Get the evolution tracking data."""
        return self._data.get("evolution", {})

    def load(self) -> bool:
        """Load the JD system from jdex.json.

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(self.jdex_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            return True
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load jdex.json: {e}")
            return False

    def save(self) -> bool:
        """Save the JD system to jdex.json.

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Update last_modified
            self._data["meta"]["last_modified"] = datetime.now().isoformat()

            # Ensure directory exists
            self.jdex_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.jdex_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving jdex.json: {e}")
            return False

    def get_areas_for_classification(self) -> dict:
        """Get areas in the format expected by classification functions.

        Converts from jdex.json format to the JD_AREAS format used by
        document_organizer.py for compatibility.

        Returns:
            Dict like {'10-19 Finance': {'11 Banking': {'keywords': [...]}, ...}}
        """
        result = {}

        for area_name, area_data in self.areas.items():
            categories = {}

            # Handle both new format (with 'categories' key) and legacy format
            if "categories" in area_data:
                for cat_name, cat_data in area_data["categories"].items():
                    categories[cat_name] = {
                        "keywords": cat_data.get("keywords", [])
                    }
            else:
                # Legacy format: area_data is directly the categories dict
                for cat_name, cat_data in area_data.items():
                    if isinstance(cat_data, dict):
                        categories[cat_name] = {
                            "keywords": cat_data.get("keywords", [])
                        }

            result[area_name] = categories

        return result

    def create_from_structure(
        self,
        areas: dict,
        generation_method: str = "manual",
        user_context: dict = None
    ) -> bool:
        """Create a new JD system from a proposed structure.

        Args:
            areas: The JD structure (areas and categories)
            generation_method: How the system was created (interview, wizard, analysis, manual)
            user_context: Optional user context info

        Returns:
            True if created successfully, False if validation failed
        """
        # Validate structure
        is_valid, errors = JDValidator.validate_structure(areas)
        if not is_valid:
            print(f"Validation errors: {errors}")
            return False

        # Set metadata
        self._data["meta"] = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "generation_method": generation_method,
            "user_context": user_context or {}
        }

        # Set areas
        self._data["areas"] = areas

        # Reset evolution
        self._data["evolution"] = {
            "total_documents": 0,
            "last_review": None,
            "next_milestone": 100,
            "pending_suggestions": [],
            "history": [{
                "timestamp": datetime.now().isoformat(),
                "action": "system_created",
                "details": f"Created via {generation_method}",
                "trigger": "initial_setup"
            }]
        }

        # Reset stats
        self._data["classification_stats"] = {
            "by_category": {},
            "low_confidence_patterns": []
        }

        return self.save()

    def add_category(
        self,
        area_name: str,
        category_name: str,
        description: str = "",
        keywords: list = None,
        reason: str = "manual"
    ) -> bool:
        """Add a new category to an existing area.

        Args:
            area_name: The area to add to (e.g., '10-19 Finance')
            category_name: The new category (e.g., '17 Crypto')
            description: Category description
            keywords: List of keywords for classification
            reason: Why the category was added

        Returns:
            True if added successfully, False otherwise
        """
        if area_name not in self.areas:
            print(f"Area not found: {area_name}")
            return False

        # Validate category belongs to area
        if not JDValidator.category_belongs_to_area(category_name, area_name):
            print(f"Category {category_name} does not belong to {area_name}")
            return False

        # Check if area has room
        existing = self.areas[area_name].get("categories", self.areas[area_name])
        if len(existing) >= JDValidator.MAX_CATEGORIES_PER_AREA:
            print(f"Area {area_name} is full (max {JDValidator.MAX_CATEGORIES_PER_AREA} categories)")
            return False

        # Add category
        if "categories" in self.areas[area_name]:
            self.areas[area_name]["categories"][category_name] = {
                "description": description,
                "keywords": keywords or [],
                "examples": [],
                "document_count": 0,
                "last_document": None
            }
        else:
            self.areas[area_name][category_name] = {
                "keywords": keywords or []
            }

        # Record in history
        self.evolution["history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "category_added",
            "details": f"Added '{category_name}' to {area_name}",
            "trigger": reason
        })

        return self.save()

    def add_area(
        self,
        area_name: str,
        description: str = "",
        categories: dict = None,
        reason: str = "manual"
    ) -> bool:
        """Add a new area to the system.

        Args:
            area_name: The new area (e.g., '60-69 Hobbies')
            description: Area description
            categories: Optional initial categories
            reason: Why the area was added

        Returns:
            True if added successfully, False otherwise
        """
        # Validate area name
        if not JDValidator.is_valid_area_name(area_name):
            print(f"Invalid area name: {area_name}")
            return False

        # Check if range is already used
        new_range = JDValidator.get_area_range(area_name)
        for existing_area in self.areas:
            existing_range = JDValidator.get_area_range(existing_area)
            if existing_range == new_range:
                print(f"Area range {new_range} already in use by {existing_area}")
                return False

        # Check area count
        non_system = [a for a in self.areas if not a.startswith("00-09")]
        if len(non_system) >= JDValidator.MAX_AREAS - 1:
            print(f"Maximum areas reached ({JDValidator.MAX_AREAS - 1} user areas)")
            return False

        # Add area
        self.areas[area_name] = {
            "description": description,
            "categories": categories or {}
        }

        # Record in history
        self.evolution["history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "area_added",
            "details": f"Added area '{area_name}'",
            "trigger": reason
        })

        return self.save()

    def record_classification(
        self,
        category_name: str,
        confidence: str,
        document_preview: str = ""
    ):
        """Record a document classification for statistics.

        Args:
            category_name: The category the document was classified into
            confidence: Classification confidence (high, medium, low)
        """
        stats = self._data["classification_stats"]["by_category"]

        if category_name not in stats:
            stats[category_name] = {"high": 0, "medium": 0, "low": 0}

        if confidence in stats[category_name]:
            stats[category_name][confidence] += 1

        # Update total documents
        self._data["evolution"]["total_documents"] += 1

        # Check for milestone
        total = self._data["evolution"]["total_documents"]
        milestone = self._data["evolution"]["next_milestone"]
        if total >= milestone:
            self._data["evolution"]["next_milestone"] = milestone + 100
            # Could trigger review notification here

    def create_folders(self) -> bool:
        """Create the folder structure on disk based on the JD system.

        Returns:
            True if created successfully
        """
        try:
            for area_name, area_data in self.areas.items():
                area_path = self.output_dir / area_name
                area_path.mkdir(parents=True, exist_ok=True)

                # Get categories
                categories = area_data.get("categories", {})
                if not categories and isinstance(area_data, dict):
                    # Legacy format check
                    categories = {k: v for k, v in area_data.items()
                                  if isinstance(v, dict) and "keywords" in v}

                for cat_name in categories:
                    cat_path = area_path / cat_name
                    cat_path.mkdir(exist_ok=True)

            return True
        except Exception as e:
            print(f"Error creating folders: {e}")
            return False


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_jd_system(output_dir: str | Path) -> JDSystem | None:
    """Get the JD system for an output directory.

    Args:
        output_dir: The JD output directory

    Returns:
        JDSystem instance if jdex.json exists, None otherwise
    """
    system = JDSystem(output_dir)
    if system.exists:
        return system
    return None


def get_jd_areas(output_dir: str | Path, fallback_areas: dict = None) -> dict:
    """Get JD areas, preferring dynamic jdex.json over fallback.

    This is the main entry point for getting JD areas, compatible with
    the existing document_organizer.py code.

    Args:
        output_dir: The JD output directory
        fallback_areas: Fallback JD_AREAS dict if no jdex.json exists

    Returns:
        JD areas dict in the format expected by classification functions
    """
    system = get_jd_system(output_dir)

    if system:
        return system.get_areas_for_classification()

    if fallback_areas:
        return copy.deepcopy(fallback_areas)

    return {}


def migrate_from_legacy(output_dir: str | Path, legacy_areas: dict) -> JDSystem:
    """Migrate from hardcoded JD_AREAS to dynamic jdex.json.

    Args:
        output_dir: The JD output directory
        legacy_areas: The legacy JD_AREAS dict

    Returns:
        The new JDSystem instance
    """
    system = JDSystem(output_dir)

    # Convert legacy format to new format
    new_areas = {}
    for area_name, categories in legacy_areas.items():
        new_areas[area_name] = {
            "description": "",
            "categories": {}
        }
        for cat_name, cat_data in categories.items():
            new_areas[area_name]["categories"][cat_name] = {
                "description": "",
                "keywords": cat_data.get("keywords", []),
                "examples": [],
                "document_count": 0,
                "last_document": None
            }

    system.create_from_structure(
        areas=new_areas,
        generation_method="migration",
        user_context={"migrated_from": "legacy_JD_AREAS"}
    )

    return system
