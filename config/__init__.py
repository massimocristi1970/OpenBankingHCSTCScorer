"""
Backward compatibility wrapper for config module.

Imports from openbanking_engine.config for backward compatibility.
New code should import from openbanking_engine.config directly.
"""

from openbanking_engine.config import (
    SCORING_CONFIG,
    PRODUCT_CONFIG,
    load_pfc_mapping,
)

__all__ = [
    "SCORING_CONFIG",
    "PRODUCT_CONFIG",
    "load_pfc_mapping",
]
