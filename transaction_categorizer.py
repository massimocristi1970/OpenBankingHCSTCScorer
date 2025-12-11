"""
Backward compatibility wrapper for TransactionCategorizer.

Imports from openbanking_engine.categorisation for backward compatibility.
New code should import from openbanking_engine.categorisation directly.
"""

from openbanking_engine.categorisation import (
    TransactionCategorizer,
    CategoryMatch,
    normalize_text,
    detect_internal_transfers,
    apply_pfc_mapping,
)

__all__ = [
    "TransactionCategorizer",
    "CategoryMatch",
    "normalize_text",
    "detect_internal_transfers",
    "apply_pfc_mapping",
]
