"""
Backward compatibility wrapper for ScoringEngine.

Imports from openbanking_engine.scoring for backward compatibility.
New code should import from openbanking_engine.scoring directly.
"""

from openbanking_engine.scoring import (
    Decision,
    RiskLevel,
    ScoreBreakdown,
    LoanOffer,
    ScoringResult,
    ScoringEngine,
)

__all__ = [
    "Decision",
    "RiskLevel",
    "ScoreBreakdown",
    "LoanOffer",
    "ScoringResult",
    "ScoringEngine",
]
