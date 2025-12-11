"""
Backward compatibility wrapper for MetricsCalculator.
Imports from the new openbanking_engine module structure.
"""

from openbanking_engine.scoring.feature_builder import (
    MetricsCalculator,
    IncomeMetrics,
    ExpenseMetrics,
    DebtMetrics,
    AffordabilityMetrics,
    BalanceMetrics,
    RiskMetrics,
)

__all__ = [
    "MetricsCalculator",
    "IncomeMetrics",
    "ExpenseMetrics",
    "DebtMetrics",
    "AffordabilityMetrics",
    "BalanceMetrics",
    "RiskMetrics",
]
