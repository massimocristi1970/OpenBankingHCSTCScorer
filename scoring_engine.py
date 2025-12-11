"""
Backward compatibility wrapper for ScoringEngine.
Imports from the new openbanking_engine module structure.
"""

from openbanking_engine.scoring.scoring_engine import (
    ScoringEngine,
    Decision,
    RiskLevel,
    ScoreBreakdown,
    ScoringResult,
)

__all__ = [
    "ScoringEngine",
    "Decision",
    "RiskLevel",
    "ScoreBreakdown",
    "ScoringResult",
]
