"""
Backward compatibility wrapper for categorization patterns and config.
Imports from the new openbanking_engine module structure.
"""

from openbanking_engine.patterns.transaction_patterns import (
    INCOME_PATTERNS,
    TRANSFER_PATTERNS,
    DEBT_PATTERNS,
    ESSENTIAL_PATTERNS,
    RISK_PATTERNS,
    POSITIVE_PATTERNS,
)

from openbanking_engine.config.scoring_config import (
    SCORING_CONFIG,
    PRODUCT_CONFIG,
)

__all__ = [
    "INCOME_PATTERNS",
    "TRANSFER_PATTERNS",
    "DEBT_PATTERNS",
    "ESSENTIAL_PATTERNS",
    "RISK_PATTERNS",
    "POSITIVE_PATTERNS",
    "SCORING_CONFIG",
    "PRODUCT_CONFIG",
]
