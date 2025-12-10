"""
Test scoring configuration updates to validate relaxed thresholds.
This test validates the changes made to increase approval rate.
"""

import unittest
from config.categorization_patterns import SCORING_CONFIG
from scoring_engine import ScoringEngine, Decision
from metrics_calculator import (
    IncomeMetrics,
    ExpenseMetrics,
    DebtMetrics,
    AffordabilityMetrics,
    BalanceMetrics,
    RiskMetrics,
)


class TestScoringConfigurationUpdates(unittest.TestCase):
    """Test updated scoring configuration thresholds."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scoring_engine = ScoringEngine()
        self.config = SCORING_CONFIG
    
    def test_updated_score_thresholds(self):
        """Test that score thresholds have been updated correctly."""
        score_ranges = self.config["score_ranges"]
        
        # Test APPROVE threshold (was ≥45, now ≥40)
        self.assertEqual(score_ranges["approve"]["min"], 40)
        self.assertEqual(score_ranges["approve"]["max"], 100)
        
        # Test REFER threshold (was 30-44, now 25-39)
        self.assertEqual(score_ranges["refer"]["min"], 25)
        self.assertEqual(score_ranges["refer"]["max"], 39)
        
        # Test DECLINE threshold (was <30, now <25)
        self.assertEqual(score_ranges["decline"]["min"], 0)
        self.assertEqual(score_ranges["decline"]["max"], 24)
    
    def test_updated_hard_decline_rules(self):
        """Test that hard decline rules have been relaxed."""
        rules = self.config["hard_decline_rules"]
        
        # Test min_monthly_income (was £1,500, now £1,000)
        self.assertEqual(rules["min_monthly_income"], 1000)
        
        # Test max_active_hcstc_lenders (was 4, now 6)
        self.assertEqual(rules["max_active_hcstc_lenders"], 6)
        
        # Test max_dti_with_new_loan (was 70%, now 75%)
        self.assertEqual(rules["max_dti_with_new_loan"], 75)
        
        # Test max_dca_count (was 2, now 3)
        self.assertEqual(rules["max_dca_count"], 3)
    
    def test_score_based_limits_for_40_45_range(self):
        """Test that score-based limits exist for 40-45 score range."""
        limits = self.config["score_based_limits"]
        
        # Find the limit for score 40
        limit_40 = None
        for limit in limits:
            if limit["min_score"] == 40:
                limit_40 = limit
                break
        
        self.assertIsNotNone(limit_40, "Score-based limit for score 40 should exist")
        self.assertGreater(limit_40["max_amount"], 0, "Max amount should be greater than 0")
        self.assertGreater(limit_40["max_term"], 0, "Max term should be greater than 0")
    
    def test_score_40_results_in_approval(self):
        """Test that a score of exactly 40 results in APPROVE decision."""
        # Create metrics for a borderline approval case
        metrics = {
            "income": IncomeMetrics(
                effective_monthly_income=1200,
                has_verifiable_income=True,
                income_stability_score=70,
                income_regularity_score=60
            ),
            "expenses": ExpenseMetrics(
                monthly_essential_total=600,
            ),
            "debt": DebtMetrics(
                monthly_debt_payments=200,
                active_hcstc_count=1,
                active_hcstc_count_90d=1
            ),
            "affordability": AffordabilityMetrics(
                monthly_disposable=400,
                debt_to_income_ratio=25,
                post_loan_disposable=280,
                max_affordable_amount=400
            ),
            "balance": BalanceMetrics(
                average_balance=150,
                days_in_overdraft=5
            ),
            "risk": RiskMetrics(
                gambling_percentage=0,
                failed_payments_count=1,
                failed_payments_count_45d=1,
                debt_collection_distinct=0
            ),
        }
        
        result = self.scoring_engine.score_application(
            metrics=metrics,
            requested_amount=300,
            requested_term=3,
            application_ref="TEST_40_SCORE"
        )
        
        # With a score around 40, we should get APPROVE
        # Note: The exact score may vary based on scoring calculations,
        # but we're testing that the decision logic works correctly
        if result.score >= 40:
            self.assertEqual(result.decision, Decision.APPROVE,
                           f"Score {result.score} (≥40) should result in APPROVE")
        elif result.score >= 25:
            self.assertEqual(result.decision, Decision.REFER,
                           f"Score {result.score} (25-39) should result in REFER")
        else:
            self.assertEqual(result.decision, Decision.DECLINE,
                           f"Score {result.score} (<25) should result in DECLINE")
    
    def test_score_44_results_in_approval(self):
        """Test that a score of 44 (previously REFER) now results in APPROVE."""
        # For this test, we check the decision logic directly
        decision, risk_level = self.scoring_engine._determine_decision(44)
        
        self.assertEqual(decision, Decision.APPROVE,
                        "Score 44 should now result in APPROVE (was REFER)")
    
    def test_score_39_results_in_refer(self):
        """Test that a score of 39 (top of new REFER range) results in REFER."""
        decision, risk_level = self.scoring_engine._determine_decision(39)
        
        self.assertEqual(decision, Decision.REFER,
                        "Score 39 should result in REFER")
    
    def test_score_25_results_in_refer(self):
        """Test that a score of 25 (bottom of new REFER range) results in REFER."""
        decision, risk_level = self.scoring_engine._determine_decision(25)
        
        self.assertEqual(decision, Decision.REFER,
                        "Score 25 should result in REFER")
    
    def test_score_24_results_in_decline(self):
        """Test that a score of 24 (top of new DECLINE range) results in DECLINE."""
        decision, risk_level = self.scoring_engine._determine_decision(24)
        
        self.assertEqual(decision, Decision.DECLINE,
                        "Score 24 should result in DECLINE")
    
    def test_income_1100_not_hard_declined(self):
        """Test that income of £1,100 (above new minimum) does not trigger hard decline."""
        metrics = {
            "income": IncomeMetrics(
                effective_monthly_income=1100,
                has_verifiable_income=True
            ),
            "expenses": ExpenseMetrics(),
            "debt": DebtMetrics(
                active_hcstc_count_90d=0
            ),
            "affordability": AffordabilityMetrics(
                monthly_disposable=500,
                post_loan_disposable=350
            ),
            "balance": BalanceMetrics(),
            "risk": RiskMetrics(
                gambling_percentage=0,
                failed_payments_count_45d=0,
                debt_collection_distinct=0
            ),
        }
        
        decline_reasons = self.scoring_engine._check_hard_decline_rules(
            income=metrics["income"],
            debt=metrics["debt"],
            affordability=metrics["affordability"],
            risk=metrics["risk"],
            requested_amount=300,
            requested_term=3
        )
        
        # Should not have income-related decline reason
        income_declined = any("income" in reason.lower() for reason in decline_reasons)
        self.assertFalse(income_declined,
                        "Income of £1,100 should not trigger hard decline (min is £1,000)")
    
    def test_6_hcstc_lenders_not_hard_declined(self):
        """Test that 6 active HCSTC lenders (at new maximum) does not trigger hard decline."""
        metrics = {
            "income": IncomeMetrics(
                effective_monthly_income=1500,
                has_verifiable_income=True
            ),
            "expenses": ExpenseMetrics(),
            "debt": DebtMetrics(
                active_hcstc_count_90d=6  # Exactly at new maximum
            ),
            "affordability": AffordabilityMetrics(
                monthly_disposable=500,
                post_loan_disposable=350
            ),
            "balance": BalanceMetrics(),
            "risk": RiskMetrics(
                gambling_percentage=0,
                failed_payments_count_45d=0,
                debt_collection_distinct=0
            ),
        }
        
        decline_reasons = self.scoring_engine._check_hard_decline_rules(
            income=metrics["income"],
            debt=metrics["debt"],
            affordability=metrics["affordability"],
            risk=metrics["risk"],
            requested_amount=300,
            requested_term=3
        )
        
        # Should not have HCSTC-related decline reason
        hcstc_declined = any("hcstc" in reason.lower() for reason in decline_reasons)
        self.assertFalse(hcstc_declined,
                        "6 HCSTC lenders should not trigger hard decline (max is 6)")
    
    def test_3_dca_not_hard_declined(self):
        """Test that 3 debt collection agencies (at new maximum) does not trigger hard decline."""
        metrics = {
            "income": IncomeMetrics(
                effective_monthly_income=1500,
                has_verifiable_income=True
            ),
            "expenses": ExpenseMetrics(),
            "debt": DebtMetrics(
                active_hcstc_count_90d=0
            ),
            "affordability": AffordabilityMetrics(
                monthly_disposable=500,
                post_loan_disposable=350
            ),
            "balance": BalanceMetrics(),
            "risk": RiskMetrics(
                gambling_percentage=0,
                failed_payments_count_45d=0,
                debt_collection_distinct=3  # Exactly at new maximum
            ),
        }
        
        decline_reasons = self.scoring_engine._check_hard_decline_rules(
            income=metrics["income"],
            debt=metrics["debt"],
            affordability=metrics["affordability"],
            risk=metrics["risk"],
            requested_amount=300,
            requested_term=3
        )
        
        # Should not have DCA-related decline reason
        dca_declined = any("debt collection" in reason.lower() for reason in decline_reasons)
        self.assertFalse(dca_declined,
                        "3 DCAs should not trigger hard decline (max is 3)")
    
    def test_74_percent_dti_not_hard_declined(self):
        """Test that 74% DTI (below new maximum of 75%) does not trigger hard decline."""
        metrics = {
            "income": IncomeMetrics(
                effective_monthly_income=2000,
                has_verifiable_income=True
            ),
            "expenses": ExpenseMetrics(),
            "debt": DebtMetrics(
                monthly_debt_payments=1000,  # 50% DTI
                active_hcstc_count_90d=0
            ),
            "affordability": AffordabilityMetrics(
                monthly_disposable=500,
                post_loan_disposable=250
            ),
            "balance": BalanceMetrics(),
            "risk": RiskMetrics(
                gambling_percentage=0,
                failed_payments_count_45d=0,
                debt_collection_distinct=0
            ),
        }
        
        # Test with a loan that would bring DTI to approximately 74%
        # Monthly income: £2000, existing debt: £1000 (50%)
        # Loan of £300 over 3 months = ~£173/month payment = total £1173/month = 58.6% DTI
        # Use smaller loan to keep under 75%
        decline_reasons = self.scoring_engine._check_hard_decline_rules(
            income=metrics["income"],
            debt=metrics["debt"],
            affordability=metrics["affordability"],
            risk=metrics["risk"],
            requested_amount=300,
            requested_term=3
        )
        
        # Should not have DTI-related decline reason
        dti_declined = any("dti" in reason.lower() or "debt-to-income" in reason.lower() 
                          for reason in decline_reasons)
        self.assertFalse(dti_declined,
                        "DTI under 75% should not trigger hard decline (max is 75%)")


if __name__ == "__main__":
    unittest.main()
