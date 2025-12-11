"""
Backward compatibility wrapper for IncomeDetector.

Imports from openbanking_engine.income for backward compatibility.
New code should import from openbanking_engine.income directly.
"""

from openbanking_engine.income import (
    IncomeDetector,
    RecurringIncomeSource,
)

__all__ = [
    "IncomeDetector",
    "RecurringIncomeSource",
]
