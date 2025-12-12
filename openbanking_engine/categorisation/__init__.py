"""
Categorisation Module for HCSTC Scoring Engine.

Orchestrates transaction categorization through:
- Preprocessing (normalization, transfer detection)
- Pattern matching (keyword and regex-based)
- PFC mapping (Plaid Personal Finance Category)
- Income detection (behavioral patterns)
"""

from .engine import TransactionCategorizer, CategoryMatch
from .preprocess import normalize_text, detect_internal_transfers, apply_pfc_mapping
from .pattern_matching import (
    match_keywords,
    match_regex_patterns,
    match_pattern_dict,
)

__all__ = [
    # Main categorizer
    "TransactionCategorizer",
    "CategoryMatch",
    # Preprocessing utilities
    "normalize_text",
    "detect_internal_transfers",
    "apply_pfc_mapping",
    # Pattern matching utilities
    "match_keywords",
    "match_regex_patterns",
    "match_pattern_dict",
]
