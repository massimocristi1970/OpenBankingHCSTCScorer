"""
Backward compatibility wrapper for IncomeDetector.
Imports from the new openbanking_engine module structure.
"""

from openbanking_engine.income.income_detector import (
    IncomeDetector,
    RecurringIncomeSource,
)

__all__ = [
    "IncomeDetector",
    "RecurringIncomeSource",
]
