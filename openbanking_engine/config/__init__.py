"""
Configuration module for OpenBanking HCSTC Scoring Engine.

This module contains all configuration dictionaries for scoring and products.
"""

from .scoring_config import SCORING_CONFIG, PRODUCT_CONFIG
from .pfc_mapping_loader import load_pfc_mapping

__all__ = [
    "SCORING_CONFIG",
    "PRODUCT_CONFIG",
    "load_pfc_mapping",
]
