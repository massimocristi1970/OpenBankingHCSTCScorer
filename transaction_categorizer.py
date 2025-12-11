"""
Backward compatibility wrapper for TransactionCategorizer.
Imports from the new openbanking_engine module structure.
"""

# Import all classes and functions from the new module
from openbanking_engine.categorisation.engine import (
    TransactionCategorizer,
    CategoryMatch,
    HCSTC_LENDER_CANONICAL_NAMES,
    HCSTC_LENDER_PATTERNS_SORTED,
)

# Re-export for backward compatibility
__all__ = [
    "TransactionCategorizer",
    "CategoryMatch",
    "HCSTC_LENDER_CANONICAL_NAMES",
    "HCSTC_LENDER_PATTERNS_SORTED",
]
