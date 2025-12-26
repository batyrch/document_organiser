#!/usr/bin/env python3
"""
JD Prompts - AI Prompts for Johnny Decimal System Generation

This module contains the AI prompts used for:
- Interview mode: Conversational system design
- Document analysis: Structure inference from document patterns
- Evolution: Low-confidence pattern detection and suggestions
"""

# ==============================================================================
# INTERVIEW MODE PROMPTS
# ==============================================================================

INTERVIEW_SYSTEM_PROMPT = """You are a Johnny Decimal organization consultant helping a user design their personal document filing system.

## Johnny Decimal Constraints (STRICT - you must enforce these)

1. **Maximum 10 areas** numbered in tens: 10-19, 20-29, 30-39, 40-49, 50-59, 60-69, 70-79, 80-89, 90-99
   - Area 00-09 is reserved for System (Index, Inbox, Templates)
   - So users get 9 areas maximum for their own use

2. **Maximum 10 categories per area** numbered within the area range
   - Example: Area "10-19 Finance" can have categories 10, 11, 12... up to 19
   - Each category must fall within its parent area's range

3. **Naming convention**
   - Areas: "XX-XX Name" (e.g., "10-19 Finance", "20-29 Medical")
   - Categories: "XX Name" (e.g., "11 Banking", "12 Taxes")

## Your Goal

Through conversation, understand the user's life and work context to design a personalized JD structure. Ask questions about:

1. **Work/life context**: Are they an employee, freelancer, student, retiree?
2. **Document types**: What kinds of documents do they handle most?
3. **Personal vs business**: Do they need to separate these?
4. **Special needs**: Any hobbies, side projects, or unique situations?
5. **Pain points**: What's frustrating about their current organization?

## Conversation Flow

- Ask ONE question at a time
- Be conversational and friendly
- After 4-6 exchanges (or when you have enough info), propose a structure
- Keep areas lean - leave room for growth (don't max out at 10 categories per area)

## Response Format

For questions, respond naturally.

When ready to propose a structure, respond with a JSON block like this:

```json
{
  "ready": true,
  "structure": {
    "10-19 Finance": {
      "description": "Personal and business finances",
      "categories": {
        "11 Banking": {
          "description": "Bank statements and accounts",
          "keywords": ["bank", "statement", "account", "transfer"]
        },
        "12 Taxes": {
          "description": "Tax returns and related documents",
          "keywords": ["tax", "return", "deduction"]
        }
      }
    },
    "20-29 Medical": {
      "description": "Health and medical documents",
      "categories": {
        "21 Records": {
          "description": "Medical records and test results",
          "keywords": ["doctor", "hospital", "diagnosis", "lab"]
        }
      }
    }
  },
  "reasoning": "Based on your freelance work and personal life, I've created..."
}
```

IMPORTANT: Always include the 00-09 System area with at least Index and Inbox categories in your proposals.

Remember: The goal is a system that helps the user find things quickly. Don't over-categorize - simpler is often better."""


INTERVIEW_INITIAL_MESSAGE = """Hi! I'm here to help you design a personalized document filing system using the Johnny Decimal method.

This system uses a simple numbering scheme:
- **Areas** (like 10-19 Finance, 20-29 Medical) group related things
- **Categories** within each area hold your actual documents

The beauty is in the constraints: maximum 10 areas, maximum 10 categories per area. This forces clarity and makes everything easy to find.

Let's start with the basics: **What do you do for work, and what's your living situation?** (For example: "I'm a freelance designer working from home" or "I'm an employee at a tech company, living with my family")"""


# ==============================================================================
# DOCUMENT ANALYSIS PROMPTS
# ==============================================================================

DOCUMENT_ANALYSIS_PROMPT = """Analyze these document summaries and propose a Johnny Decimal structure that would organize them effectively.

## Document Summaries
{document_summaries}

## Your Task

Based on patterns in these documents, propose a JD structure that:

1. Groups related documents into logical areas
2. Creates specific categories within each area
3. Includes relevant keywords for each category (for auto-classification)
4. Leaves room for growth (don't max out categories)

## Constraints (STRICT)

- Maximum 9 user areas (00-09 is reserved for System)
- Maximum 10 categories per area
- Area naming: "XX-XX Name" (e.g., "10-19 Finance")
- Category naming: "XX Name" (e.g., "11 Banking")
- Categories must fall within their parent area's numeric range

## Response Format

```json
{
  "proposed_structure": {
    "00-09 System": {
      "description": "System folders",
      "categories": {
        "00 Index": {"description": "Master index", "keywords": []},
        "01 Inbox": {"description": "Incoming documents", "keywords": []}
      }
    },
    "10-19 Finance": {
      "description": "Financial documents",
      "categories": {
        "11 Banking": {
          "description": "Bank statements and account documents",
          "keywords": ["bank", "statement", "account"]
        }
      }
    }
  },
  "document_distribution": {
    "11 Banking": 34,
    "21 Medical Records": 12
  },
  "uncategorized_count": 5,
  "suggestions": [
    "Consider adding a category for...",
    "Many documents mention X, which could be..."
  ]
}
```"""


# ==============================================================================
# EVOLUTION PROMPTS
# ==============================================================================

LOW_CONFIDENCE_ANALYSIS_PROMPT = """Analyze these documents that received low classification confidence and determine if the JD system needs adjustment.

## Low-Confidence Documents
{low_confidence_documents}

## Current JD Structure
{current_structure}

## Your Task

Determine the best course of action:

1. **New category needed**: If documents share a clear theme not covered by existing categories
2. **Keywords to add**: If documents would fit existing category with better keywords
3. **No action needed**: If documents are genuinely miscellaneous or one-offs

## Response Format

```json
{
  "recommendation": "new_category",
  "confidence": 0.85,
  "details": {
    "suggested_area": "10-19 Finance",
    "suggested_category": "17 Crypto",
    "suggested_keywords": ["crypto", "bitcoin", "ethereum", "wallet", "blockchain"],
    "description": "Cryptocurrency and digital asset documents",
    "affected_documents": ["doc1.pdf", "doc2.pdf"]
  },
  "reasoning": "15 documents consistently mention cryptocurrency terms..."
}
```

Or for keyword addition:

```json
{
  "recommendation": "add_keywords",
  "confidence": 0.72,
  "details": {
    "target_category": "14 Receipts",
    "new_keywords": ["subscription", "recurring", "monthly"],
    "affected_documents": ["doc1.pdf", "doc2.pdf"]
  },
  "reasoning": "These subscription receipts would match better with..."
}
```

Or for no action:

```json
{
  "recommendation": "no_action",
  "confidence": 0.65,
  "reasoning": "Documents are too diverse to warrant a new category..."
}
```"""


REORGANIZATION_PROMPT = """Review this JD system's usage statistics and suggest improvements.

## Current Structure
{current_structure}

## Usage Statistics
{usage_stats}

## Issues to Consider

- Categories with >100 documents may need splitting
- Categories with 0 documents may be unnecessary
- High overlap between categories may suggest merging
- Consistent low-confidence areas indicate unclear categorization

## Constraints

- Stay within JD limits (max 10 areas, 10 categories each)
- Prefer adding keywords over restructuring (less disruptive)
- Consider migration effort for each suggestion

## Response Format

```json
{
  "suggestions": [
    {
      "type": "split_category",
      "priority": "high",
      "current": "14 Receipts",
      "proposed": ["14 Online Purchases", "15 In-Store Receipts"],
      "reason": "156 documents would benefit from finer categorization",
      "affected_documents": 156,
      "effort": "medium"
    },
    {
      "type": "add_keywords",
      "priority": "low",
      "category": "12 Taxes",
      "new_keywords": ["1099", "W-2"],
      "reason": "Would improve classification of US tax forms",
      "affected_documents": 0,
      "effort": "low"
    }
  ],
  "overall_health_score": 0.82,
  "summary": "System is generally well-organized. One high-priority split recommended..."
}
```"""


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_interview_messages(conversation_history: list) -> list:
    """Format conversation history for the interview prompt.

    Args:
        conversation_history: List of {"role": "user"|"assistant", "content": str}

    Returns:
        Messages formatted for the AI provider
    """
    messages = []

    # Add initial message if conversation is empty
    if not conversation_history:
        messages.append({
            "role": "assistant",
            "content": INTERVIEW_INITIAL_MESSAGE
        })
    else:
        messages = conversation_history.copy()

    return messages


def parse_structure_from_response(response: str) -> dict | None:
    """Extract JSON structure from an AI response.

    Args:
        response: The AI's response text

    Returns:
        Parsed structure dict if found, None otherwise
    """
    import json
    import re

    # Try to find JSON block in response
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)

    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if data.get("ready") and "structure" in data:
                return data
        except json.JSONDecodeError:
            pass

    # Try parsing the whole response as JSON
    try:
        data = json.loads(response)
        if data.get("ready") and "structure" in data:
            return data
    except json.JSONDecodeError:
        pass

    return None
