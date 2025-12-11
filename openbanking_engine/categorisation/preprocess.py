"""
Transaction Preprocessing for HCSTC Scoring Engine.

Handles transaction normalization, internal transfer detection, and PFC mapping.
Future enhancement: Extract preprocessing logic from TransactionCategorizer into reusable functions.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


def normalize_text(text: str) -> str:
    """
    Normalize transaction text for pattern matching.
    
    Args:
        text: Raw transaction description
        
    Returns:
        Normalized uppercase text
    """
    if not text:
        return ""
    return str(text).upper().strip()


def detect_internal_transfers(
    transactions: List[Dict],
    amount_tolerance: float = 0.01,
    date_tolerance_days: int = 1
) -> List[Tuple[int, int]]:
    """
    Detect potential internal transfers using naive matching.
    
    Matches transactions with:
    - Similar amounts (within tolerance)
    - Similar descriptions (fuzzy match)
    - Dates within tolerance
    - Opposite directions (credit vs debit)
    
    Args:
        transactions: List of transaction dicts with 'amount', 'description', 'date'
        amount_tolerance: Max difference in absolute amounts
        date_tolerance_days: Max days between matching transactions
        
    Returns:
        List of (index1, index2) tuples representing matched pairs
    """
    # Placeholder implementation
    # In future, this could be extracted from TransactionCategorizer
    return []


def apply_pfc_mapping(
    plaid_category: Optional[str],
    pfc_mapping: Dict[str, Dict[str, str]]
) -> Optional[Tuple[str, str]]:
    """
    Apply PFC (Plaid Personal Finance Category) mapping.
    
    Args:
        plaid_category: PLAID category string
        pfc_mapping: Dictionary mapping PLAID categories to engine categories
        
    Returns:
        Tuple of (category, subcategory) or None if no mapping found
    """
    if not plaid_category or not pfc_mapping:
        return None
    
    mapping = pfc_mapping.get(plaid_category)
    if mapping:
        return (mapping.get('category'), mapping.get('subcategory'))
    
    return None
