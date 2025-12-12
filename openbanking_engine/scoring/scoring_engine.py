"""
HCSTC Scoring Engine for Loan Applications.
Implements scoring system with hard decline rules and score-based loan limits.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..config.scoring_config import SCORING_CONFIG, PRODUCT_CONFIG
from .feature_builder import (
    IncomeMetrics,
    ExpenseMetrics,
    DebtMetrics,
    AffordabilityMetrics,
    BalanceMetrics,
    RiskMetrics,
)


class Decision(Enum):
    """Loan decision outcomes."""
    APPROVE = "APPROVE"
    REFER = "REFER"
    DECLINE = "DECLINE"


class RiskLevel(Enum):
    """Risk level classifications."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


@dataclass
class ScoreBreakdown:
    """Detailed score breakdown by component."""
    affordability_score: float = 0.0
    affordability_breakdown: Dict = field(default_factory=dict)
    
    income_quality_score: float = 0.0
    income_breakdown: Dict = field(default_factory=dict)
    
    account_conduct_score: float = 0.0
    conduct_breakdown: Dict = field(default_factory=dict)
    
    risk_indicators_score: float = 0.0
    risk_breakdown: Dict = field(default_factory=dict)
    
    total_score: float = 0.0
    penalties_applied: List[str] = field(default_factory=list)


@dataclass
class LoanOffer:
    """Loan offer details."""
    approved_amount: float = 0.0
    approved_term: int = 0
    monthly_repayment: float = 0.0
    total_repayable: float = 0.0
    apr: float = 0.0
    interest_rate: float = 0.0


@dataclass
class ScoringResult:
    """Complete scoring result for an application."""
    application_ref: str = ""
    decision: Decision = Decision.DECLINE
    score: float = 0.0
    risk_level: RiskLevel = RiskLevel.HIGH
    
    loan_offer: Optional[LoanOffer] = None
    score_breakdown: Optional[ScoreBreakdown] = None
    
    # Affordability summary
    monthly_income: float = 0.0
    monthly_expenses: float = 0.0
    monthly_disposable: float = 0.0
    post_loan_disposable: float = 0.0
    
    # Risk flags
    risk_flags: List[str] = field(default_factory=list)
    decline_reasons: List[str] = field(default_factory=list)
    
    # Processing info
    processing_notes: List[str] = field(default_factory=list)


class ScoringEngine:
    """HCSTC loan scoring engine."""
    
    def __init__(self):
        """Initialize the scoring engine with configuration."""
        self.scoring_config = SCORING_CONFIG
        self.product_config = PRODUCT_CONFIG
        self.weights = self.scoring_config["weights"]
        self.thresholds = self.scoring_config["thresholds"]
        self.hard_decline_rules = self.scoring_config["hard_decline_rules"]
        self.score_based_limits = self.scoring_config["score_based_limits"]
    
    def score_application(
        self,
        metrics: Dict,
        requested_amount: float = 500,
        requested_term: int = 4,
        application_ref: str = ""
    ) -> ScoringResult:
        """
        Score a loan application based on calculated metrics.
        
        Args:
            metrics: Dictionary containing all metric objects
            requested_amount: Requested loan amount
            requested_term: Requested loan term in months
            application_ref: Application reference number
        
        Returns:
            ScoringResult with decision and details
        """
        income = metrics.get("income", IncomeMetrics())
        expenses = metrics.get("expenses", ExpenseMetrics())
        debt = metrics.get("debt", DebtMetrics())
        affordability = metrics.get("affordability", AffordabilityMetrics())
        balance = metrics.get("balance", BalanceMetrics())
        risk = metrics.get("risk", RiskMetrics())
        
        # Initialize result
        result = ScoringResult(
            application_ref=application_ref,
            monthly_income=income.effective_monthly_income,
            monthly_expenses=expenses.monthly_essential_total + debt.monthly_debt_payments,
            monthly_disposable=affordability.monthly_disposable,
            post_loan_disposable=affordability.post_loan_disposable,
        )
        
        # Check hard decline rules first
        decline_reasons = self._check_hard_decline_rules(
            income=income,
            debt=debt,
            affordability=affordability,
            risk=risk,
            requested_amount=requested_amount,
            requested_term=requested_term
        )
        
        if decline_reasons:
            result.decision = Decision.DECLINE
            result.decline_reasons = decline_reasons
            result.score = 0.0
            result.risk_level = RiskLevel.VERY_HIGH
            return result
        
        # Calculate score breakdown
        score_breakdown = self._calculate_scores(
            income=income,
            affordability=affordability,
            balance=balance,
            risk=risk,
            debt=debt
        )
        
        result.score_breakdown = score_breakdown
        result.score = score_breakdown.total_score
        
        # Determine decision based on score
        decision, risk_level = self._determine_decision(score_breakdown.total_score)
        result.decision = decision
        result.risk_level = risk_level
        
        # Collect risk flags
        result.risk_flags = self._collect_risk_flags(risk, debt, affordability, balance)
        
        # Determine loan offer if approved
        if decision == Decision.APPROVE:
            loan_offer = self._determine_loan_offer(
                score=score_breakdown.total_score,
                affordability=affordability,
                requested_amount=requested_amount,
                requested_term=requested_term
            )
            result.loan_offer = loan_offer
            result.post_loan_disposable = (
                affordability.monthly_disposable - loan_offer.monthly_repayment
            )
        elif decision == Decision.REFER:
            result.processing_notes = ["Manual review required"]
        
        return result
    
    def _check_hard_decline_rules(
        self,
        income: IncomeMetrics,
        debt: DebtMetrics,
        affordability: AffordabilityMetrics,
        risk: RiskMetrics,
        requested_amount: float,
        requested_term: int
    ) -> List[str]:
        """Check hard decline rules and return reasons if any apply."""
        reasons = []
        rules = self.hard_decline_rules
        
        # Rule 1: Monthly income < £500
        if income.effective_monthly_income is not None and income.effective_monthly_income < rules["min_monthly_income"]:
            reasons.append(
                f"Monthly income (£{income.effective_monthly_income:.2f}) "
                f"below minimum (£{rules['min_monthly_income']})"
            )
        
        # Rule 2: No identifiable income source
        if not income.has_verifiable_income and income.effective_monthly_income is not None and income.effective_monthly_income < 300:
            reasons.append("No verifiable income source identified")
        
        # Rule 3: Active HCSTC with too many lenders in last 90 days
        if debt.active_hcstc_count_90d is not None and debt.active_hcstc_count_90d > rules["max_active_hcstc_lenders"]:
            reasons.append(
                f"Active HCSTC with {debt.active_hcstc_count_90d} lenders in last 90 days "
                f"(maximum {rules['max_active_hcstc_lenders']})"
            )
        
        # Rule 4: Gambling > 15% of income
        if risk.gambling_percentage is not None and risk.gambling_percentage > rules["max_gambling_percentage"]:
            reasons.append(
                f"Gambling ({risk.gambling_percentage:.1f}%) exceeds "
                f"maximum ({rules['max_gambling_percentage']}%)"
            )
        
        # Rule 5: Post-loan disposable < £30
        if affordability.post_loan_disposable is not None and affordability.post_loan_disposable < rules["min_post_loan_disposable"]:
            reasons.append(
                f"Post-loan disposable (£{affordability.post_loan_disposable:.2f}) "
                f"below minimum (£{rules['min_post_loan_disposable']})"
            )
        
        # Rule 6: Too many failed payments in last 45 days
        if risk.failed_payments_count_45d is not None and risk.failed_payments_count_45d > rules["max_failed_payments"]:
            reasons.append(
                f"Failed payments ({risk.failed_payments_count_45d}) in last 45 days exceed "
                f"maximum ({rules['max_failed_payments']})"
            )
        
        # Rule 7: Active debt collection (3+ DCAs)
        if risk.debt_collection_distinct is not None and risk.debt_collection_distinct > rules["max_dca_count"]:
            reasons.append(
                f"Active debt collection with {risk.debt_collection_distinct} agencies "
                f"(maximum {rules['max_dca_count']})"
            )
        
        # Rule 8: DTI would exceed maximum threshold with new loan
        new_loan_payment = self._calculate_monthly_payment(
            requested_amount, requested_term
        )
        if income.effective_monthly_income is not None and income.effective_monthly_income > 0:
            projected_dti = (
                (debt.monthly_debt_payments + new_loan_payment) / 
                income.effective_monthly_income * 100
            )
            if projected_dti > rules["max_dti_with_new_loan"]:
                reasons.append(
                    f"Projected DTI ({projected_dti:.1f}%) would exceed "
                    f"maximum ({rules['max_dti_with_new_loan']}%)"
                )
        
        return reasons
    
    def _calculate_scores(
        self,
        income: IncomeMetrics,
        affordability: AffordabilityMetrics,
        balance: BalanceMetrics,
        risk: RiskMetrics,
        debt: DebtMetrics
    ) -> ScoreBreakdown:
        """Calculate detailed score breakdown."""
        breakdown = ScoreBreakdown()
        penalties = []
        
        # 1. Affordability Score (78.75 points, previously 45)
        aff_weights = self.weights["affordability"]
        
        # DTI Ratio (31.5 points, previously 18)
        dti_points = self._score_threshold(
            affordability.debt_to_income_ratio,
            self.thresholds["dti_ratio"],
            is_lower_better=True
        )
        
        # Disposable Income (26.25 points, previously 15)
        disp_points = self._score_threshold(
            affordability.monthly_disposable,
            self.thresholds["disposable_income"],
            is_lower_better=False
        )
        
        # Post-loan Affordability (21 points, previously 12)
        if affordability.post_loan_disposable is not None:
            post_loan_points = min(21, max(0, affordability.post_loan_disposable / 50 * 21))
        else:
            post_loan_points = 0
        
        affordability_score = dti_points + disp_points + post_loan_points
        breakdown.affordability_score = min(affordability_score, aff_weights["total"])
        breakdown.affordability_breakdown = {
            "dti_ratio": round(dti_points, 1),
            "disposable_income": round(disp_points, 1),
            "post_loan_affordability": round(post_loan_points, 1),
        }
        
        # 2. Income Quality Score (43.75 points, previously 25)
        inc_weights = self.weights["income_quality"]
        
        # Income Stability (21 points, previously 12)
        stability_points = self._score_threshold(
            income.income_stability_score,
            self.thresholds["income_stability"],
            is_lower_better=False
        )
        
        # Income Regularity (14 points, previously 8)
        if income.income_regularity_score is not None:
            regularity_points = min(14, income.income_regularity_score / 100 * 14)
        else:
            regularity_points = 0
        
        # Income Verification (8.75 points, previously 5)
        verification_points = 8.75 if income.has_verifiable_income else 3.5
        
        income_score = stability_points + regularity_points + verification_points
        breakdown.income_quality_score = min(income_score, inc_weights["total"])
        breakdown.income_breakdown = {
            "income_stability": round(stability_points, 1),
            "income_regularity": round(regularity_points, 1),
            "income_verification": round(verification_points, 1),
        }
        
        # 3. Account Conduct Score (35 points, previously 20)
        conduct_weights = self.weights["account_conduct"]
        
        # Failed Payments (14 points, previously 8)
        if risk.failed_payments_count is not None:
            failed_points = max(0, 14 - risk.failed_payments_count * 3.5)
        else:
            failed_points = 0
        
        # Overdraft Usage (12.25 points, previously 7)
        if balance.days_in_overdraft is not None:
            if balance.days_in_overdraft == 0:
                overdraft_points = 12.25
            elif balance.days_in_overdraft <= 5:
                overdraft_points = 8.75
            elif balance.days_in_overdraft <= 15:
                overdraft_points = 5.25
            else:
                overdraft_points = 0
        else:
            overdraft_points = 0
        
        # Balance Management (8.75 points, previously 5)
        if balance.average_balance is not None:
            if balance.average_balance >= 500:
                balance_points = 8.75
            elif balance.average_balance >= 200:
                balance_points = 5.25
            elif balance.average_balance >= 0:
                balance_points = 1.75
            else:
                balance_points = 0
        else:
            balance_points = 0
        
        conduct_score = failed_points + overdraft_points + balance_points
        breakdown.account_conduct_score = min(conduct_score, conduct_weights["total"])
        breakdown.conduct_breakdown = {
            "failed_payments": round(failed_points, 1),
            "overdraft_usage": round(overdraft_points, 1),
            "balance_management": round(balance_points, 1),
        }
        
        # 4. Risk Indicators Score (17.5 points, previously 10)
        risk_weights = self.weights["risk_indicators"]
        
        # Gambling Activity (8.75 points, previously 5)
        gambling_points = self._score_threshold(
            risk.gambling_percentage,
            self.thresholds["gambling_percentage"],
            is_lower_better=True
        )
        
        # HCSTC History (8.75 points, previously 5)
        if debt.active_hcstc_count is not None:
            if debt.active_hcstc_count == 0:
                hcstc_points = 8.75
            elif debt.active_hcstc_count == 1:
                hcstc_points = 3.5
            else:
                hcstc_points = 0
                penalties.append(f"Multiple HCSTC lenders ({debt.active_hcstc_count})")
        else:
            hcstc_points = 0
        
        risk_score = gambling_points + hcstc_points
        breakdown.risk_indicators_score = risk_score
        breakdown.risk_breakdown = {
            "gambling_activity": round(gambling_points, 1),
            "hcstc_history": round(hcstc_points, 1),
        }
        
        # Apply penalties (scaled by 1.75x)
        if risk.gambling_percentage is not None and risk.gambling_percentage > 5:
            penalty = -8.75  # Previously -5
            penalties.append(f"Gambling penalty: {penalty}")
            risk_score += penalty
        
        if debt.active_hcstc_count is not None and debt.active_hcstc_count >= 2:
            penalty = -17.5  # Previously -10
            penalties.append(f"Multiple HCSTC penalty: {penalty}")
            risk_score += penalty
        
        breakdown.penalties_applied = penalties
        
        # Total Score (max 175, previously 100)
        breakdown.total_score = max(0, min(175, 
            breakdown.affordability_score +
            breakdown.income_quality_score +
            breakdown.account_conduct_score +
            breakdown.risk_indicators_score
        ))
        
        return breakdown
    
    def _score_threshold(
        self, 
        value: float, 
        thresholds: List[Dict],
        is_lower_better: bool
    ) -> float:
        """Score a value against threshold table."""
        # Handle None values - return lowest score (0 points)
        if value is None:
            return 0
        
        for threshold in thresholds:
            if is_lower_better:
                if "max" in threshold and value <= threshold["max"]:
                    return threshold["points"]
            else:
                if "min" in threshold and value >= threshold["min"]:
                    return threshold["points"]
        
        # Return last threshold's points as default
        return thresholds[-1].get("points", 0)
    
    def _determine_decision(self, score: float) -> Tuple[Decision, RiskLevel]:
        """Determine decision and risk level from score."""
        ranges = self.scoring_config["score_ranges"]
        
        if score >= ranges["approve"]["min"]:
            return Decision.APPROVE, RiskLevel.LOW
        elif score >= ranges["refer"]["min"]:
            return Decision.REFER, RiskLevel.HIGH
        else:
            return Decision.DECLINE, RiskLevel.VERY_HIGH
    
    def _collect_risk_flags(
        self,
        risk: RiskMetrics,
        debt: DebtMetrics,
        affordability: AffordabilityMetrics,
        balance: BalanceMetrics
    ) -> List[str]:
        """Collect risk flags for the application."""
        flags = []
        
        if risk.gambling_percentage is not None and risk.gambling_percentage > 0:
            flags.append(f"Gambling: {risk.gambling_percentage:.1f}% of income")
        
        if debt.active_hcstc_count_90d is not None and debt.active_hcstc_count_90d > 0:
            flags.append(f"Active HCSTC (90d): {debt.active_hcstc_count_90d} lenders")
        
        if risk.failed_payments_count_45d is not None and risk.failed_payments_count_45d > 0:
            flags.append(f"Failed payments (45d): {risk.failed_payments_count_45d}")
        
        if risk.debt_collection_distinct is not None and risk.debt_collection_distinct > 0:
            flags.append(f"Debt collection: {risk.debt_collection_distinct} agencies")
        
        if balance.days_in_overdraft is not None and balance.days_in_overdraft > 10:
            flags.append(f"Overdraft: {balance.days_in_overdraft} days")
        
        if affordability.debt_to_income_ratio is not None and affordability.debt_to_income_ratio > 40:
            flags.append(f"High DTI: {affordability.debt_to_income_ratio:.1f}%")
        
        return flags
    
    def _determine_loan_offer(
        self,
        score: float,
        affordability: AffordabilityMetrics,
        requested_amount: float,
        requested_term: int
    ) -> LoanOffer:
        """Determine the loan offer based on score and affordability."""
        
        # Get score-based limits
        score_limit = 0
        max_term = 0
        for limit in self.score_based_limits:
            if score >= limit["min_score"]:
                score_limit = limit["max_amount"]
                max_term = limit["max_term"]
                break
        
        # Calculate affordability-based maximum
        aff_max = affordability.max_affordable_amount if affordability.max_affordable_amount is not None else 0
        
        # Final approved amount is minimum of all limits
        approved_amount = min(
            requested_amount,
            self.product_config["max_loan_amount"],
            score_limit,
            aff_max
        )
        
        # Ensure minimum loan amount
        if approved_amount < self.product_config["min_loan_amount"]:
            approved_amount = 0
        
        # Adjust term
        approved_term = min(requested_term, max_term)
        if approved_term < 3:
            approved_term = 3
        
        # Calculate repayment
        monthly_payment = self._calculate_monthly_payment(approved_amount, approved_term)
        total_repayable = monthly_payment * approved_term
        
        # Calculate simplified APR for display purposes only.
        # NOTE: For production use, this should implement the proper APR calculation
        # methodology required by UK Consumer Credit Act and FCA regulations.
        # The actual APR calculation involves solving for the internal rate of return
        # of the cash flows and annualizing it according to specific regulatory rules.
        # This simplified version is for indicative purposes only.
        if approved_amount > 0:
            interest = total_repayable - approved_amount
            apr = (interest / approved_amount) * (12 / approved_term) * 100
        else:
            apr = 0
        
        return LoanOffer(
            approved_amount=round(approved_amount, 2),
            approved_term=approved_term,
            monthly_repayment=round(monthly_payment, 2),
            total_repayable=round(total_repayable, 2),
            apr=round(apr, 1),
            interest_rate=self.product_config["daily_interest_rate"] * 100
        )
    
    def _calculate_monthly_payment(
        self, 
        amount: float, 
        term: int
    ) -> float:
        """Calculate monthly payment for a loan."""
        if amount <= 0 or term <= 0:
            return 0.0
        
        daily_rate = self.product_config["daily_interest_rate"]
        days_per_month = 30.4
        monthly_rate = daily_rate * days_per_month
        
        # Total interest capped at 100%
        total_interest = min(
            amount * monthly_rate * term,
            amount * self.product_config["total_cost_cap"]
        )
        
        total_repayable = amount + total_interest
        return total_repayable / term
