"""
Backward compatibility wrapper for MetricsCalculator.

Imports from openbanking_engine.scoring.feature_builder for backward compatibility.
New code should import from openbanking_engine.scoring directly.
"""

from openbanking_engine.scoring import (
    IncomeMetrics,
    ExpenseMetrics,
    DebtMetrics,
    AffordabilityMetrics,
    BalanceMetrics,
    RiskMetrics,
    MetricsCalculator,
)

__all__ = [
    "IncomeMetrics",
    "ExpenseMetrics",
    "DebtMetrics",
    "AffordabilityMetrics",
    "BalanceMetrics",
    "RiskMetrics",
    "MetricsCalculator",
]
